import pathlib
import random
from typing import Dict, List, Tuple

import click
import numpy as np
import toml
import torch.utils.tensorboard

from ._helpers import echo_item, parse_region_selector
from .. import sources
from .. import filters
from ..analysis import TimeSeries
from ..modelling import Model
from ..storage import Storage


_RegionKey = Tuple[str, str]


def _init_storage(storage: Storage, config: dict, regions: List[str]):
    '''Initialize the database to process the list of regions.

    Parameters
    ----------
    storage : Storage
        an uninitialized storage object that will be set up to get data for the
        list of regions
    config : dict
        a dictionary containing the general database configuration
    regions : List[str]
        the list of regions that the database will work with
    '''
    for region in regions:
        source = sources.init_source(config['storage'], False, region,
                                     config['sources'])
        storage.populate(source)


def _generate_dataset(storage: Storage, regions: List[str],
                      features: List[str]) -> Dict[_RegionKey, np.ndarray]:
    '''Generates a training-friendly dataset from the database.

    Parameters
    ----------
    storage : Storage
        an initialized storage object
    regions : List[str]
        a list of regions to use as the input datasets
    features : List[str]
        a list of features used for the feature space

    Returns
    -------
    dict
        a dictionary containing the prepared datasets
    '''
    training_data: Dict[_RegionKey, np.ndarray] = {}
    for region in regions:
        country, province = parse_region_selector(region)
        source = sources.select_source(region).name()
        cases = storage.cases(source, country, province)
        cases = filters.sum_by_date(cases)

        sample = []
        for feature in features:
            series = TimeSeries(cases, feature)
            sample.append(series.daily_change)

        training_data[(country, province)] = np.array(sample)

    return training_data


@click.command('model')
@click.option('--tensorboard', is_flag=True,
              help='Write training status to tensorboard.')
@click.argument('settings_path', metavar='SETTINGS',
                type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.pass_obj
def command(config: dict, tensorboard: bool, settings_path: str):
    '''Train an ARIMA-like RNN model on given COVID-19 case data.

    The model attempts to predict the number of case count N-days into the
    future, given current observations.  It assumes each day is a draw from an
    unknown, non-stationary stochastic process that, over the short term,
    appears Poisson-like.
    '''
    with pathlib.Path(settings_path).open() as f:
        settings = toml.load(f)

    model_config = settings['modelling']['configuration']
    training_config = settings['modelling']['training']

    click.secho('Training Prediction Model', bold=True)
    if tensorboard:
        click.secho('Tensorboard: ', bold=True, nl=False)
        click.secho('\u2713', fg='green')

    echo_item('Epochs', f'{training_config["epochs"]}')
    echo_item('Learning Rate', f'{training_config["learning_rate"]}')
    echo_item('Look-ahead', f'{model_config["lookahead_window"]} days')
    echo_item('Initial Alpha', f'{model_config["initial_alpha"]}')

    click.secho('Features:', bold=True)
    for feature in model_config['features']:
        click.echo(f'  - {feature}')

    click.secho('Regions:', bold=True)
    for region in training_config['regions']:
        click.echo(f'  - {region}')

    # Get all of the training data from the data sources.
    with Storage() as storage:
        regions = training_config['regions']
        features = model_config['features']
        _init_storage(storage, config, regions)
        training_data = _generate_dataset(storage, regions, features)

    # Now run the training the loop.
    if tensorboard:
        writer = torch.utils.tensorboard.SummaryWriter()
        region_index = 0

    loss = []
    model = Model(len(model_config['features']), model_config['hidden_states'],
                  training_config['learning_rate'])

    click.secho('Training:', bold=True)
    with click.progressbar(range(training_config['epochs'])) as epochs:
        for epoch in epochs:
            batch = random.sample(training_data.keys(), len(training_data))

            batch_loss = 0
            for region in batch:
                region_loss = model.train(training_data[region])
                batch_loss += region_loss
                if tensorboard:
                    writer.add_scalar('Region Loss', region_loss, region_index)
                    region_index += 1

            loss.append(batch_loss / len(batch))
            if tensorboard:
                writer.add_scalar('Batch Loss', loss[-1], epoch)

    if tensorboard:
        writer.close()

import pathlib
from typing import Dict, Tuple

import click
import numpy as np
import toml

from ._helpers import echo_item, parse_region_selector
from .. import sources
from .. import filters
from ..analysis import TimeSeries
from ..storage import Storage


_RegionKey = Tuple[str, str]


@click.command('model')
@click.argument('settings_path', metavar='SETTINGS',
                type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.pass_obj
def command(config: dict, settings_path: str):
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
        for region in training_config['regions']:
            source = sources.init_source(config['storage'], False, region,
                                         config['sources'])
            storage.populate(source)

        # Generate the training data.
        training_data: Dict[_RegionKey, np.ndarray] = {}
        for region in training_config['regions']:
            country, province = parse_region_selector(region)
            source = sources.select_source(region).name()
            cases = storage.cases(source, country, province)
            cases = filters.sum_by_date(cases)

            sample = []
            for feature in model_config['features']:
                series = TimeSeries(cases, feature)
                sample.append(series.daily_change)

            training_data[(country, province)] = np.array(sample)

    # Now run the training the loop.

import pathlib
import random
from typing import Dict, List, Tuple

import bokeh.io
import bokeh.layouts
import bokeh.plotting
import click
import numpy as np
import toml
import torch
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


def _training_report(output: str, model: Model, loss: List[float],
                     samples: Dict[_RegionKey, np.ndarray]):
    '''Generates a training report.

    Parameters
    ----------
    output : str
        name of the output file
    model : :class:`Model`
        the trained model
    loss : list of float
        batch losses during training
    samples : dict
        samples used to show prediction/filtering performance
    '''
    alpha = model.prefilter.alpha.detach().item()
    bokeh.io.output_file(output, title='Training Report')

    loss_fig = bokeh.plotting.figure(
        x_axis_label='Epoch',
        y_axis_label='Loss',
        y_axis_type='log',
        title='Training Loss'
    )
    loss_fig.line(range(len(loss)), loss)

    samples_layout = []
    for region, original in samples.items():
        recovered = model.reconstruct(original)

        prediction = bokeh.plotting.figure(title=':'.join(region))
        prediction.line(np.arange(original.shape[1]), original.squeeze(),
                        legend_label='Original')
        prediction.line(np.arange(recovered.shape[0]), recovered.squeeze(),
                        line_width=2, line_color='orange',
                        legend_label='Predicted Lambda')

        smoothed = bokeh.plotting.figure(title=':'.join(region))
        smoothed.line(np.arange(original.shape[1]), original.squeeze(),
                      legend_label='Original')
        smoothed.line(np.arange(original.shape[1]), model.filter(original),
                      line_width=2, line_color='green',
                      legend_label=f'Filtered (a={alpha:.2})')

        samples_layout.append([prediction, smoothed])

    bokeh.io.show(
        bokeh.layouts.grid([
            [loss_fig],
            [samples_layout]
        ])
    )


@click.command('model')
@click.option('--tensorboard', is_flag=True,
              help='Write training status to tensorboard.')
@click.option('--training-report', is_flag=True,
              help='Generate a training report.')
@click.option('--output', '-o', 'model_path', type=click.Path(dir_okay=False),
              help='Output location for the saved model.', default='model.pth')
@click.argument('settings_path', metavar='SETTINGS',
                type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.pass_obj
def command(config: dict, tensorboard: bool, training_report: bool,
            model_path: str, settings_path: str):
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
    model = Model(len(model_config['features']),
                  model_config['lookahead_window'],
                  model_config['hidden_states'],
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
                    writer.add_scalar('Loss/Region', region_loss, region_index)
                    region_index += 1

            loss.append(batch_loss / len(batch))
            if tensorboard:
                writer.add_scalar('Loss/Batch', loss[-1], epoch)
                with torch.no_grad():
                    writer.add_scalar(
                        'Param/alpha', model.prefilter.alpha.detach().numpy(),
                        epoch)

    model.save('model.pth')

    if tensorboard:
        writer.close()

    # Generate a Bokeh "report".
    if training_report:
        samples = {
            ('Canada', 'Alberta'): training_data[('Canada', 'Alberta')],
            ('Canada', 'Ontario'): training_data[('Canada', 'Ontario')],
            ('Canada', 'Quebec'): training_data[('Canada', 'Quebec')],
        }
        _training_report('training.html', model, loss, samples)

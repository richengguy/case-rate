import datetime
import json
import pathlib
from typing import Any, Dict, List, Tuple

import click
import numpy as np

from ._helpers import _parse_region_selector
from .. import analysis, sources
from .._types import Cases, PathLike
from ..analysis import TimeSeries
from ..report import SourceInfo
from ..storage import Storage


def _datatype_converter(obj):
    if isinstance(obj, datetime.date) or isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()


def _process_country_name(country: str) -> str:
    return country.replace(':', '_')


def _output_configuration(output_folder: PathLike,
                          source_info: Dict[str, SourceInfo],
                          min_confirmed: int, filter_window: int):
    output_folder = pathlib.Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    generation_time = datetime.datetime.now() \
        .astimezone() \
        .replace(microsecond=0)

    configuration = {
        'generated': generation_time,
        'regions': [
            {
                'name': name,
                'url': info.url,
                'description': info.description
            }
            for name, info in source_info.items()
        ],
        'config': {
            'filterWindow': filter_window,
            'minConfirmed': min_confirmed,
        }
    }

    analysis_file = output_folder / 'analysis.json'
    click.echo(f'Writing {analysis_file}...', nl=False)
    with analysis_file.open('wt') as f:
        json.dump(configuration, f, default=_datatype_converter, indent=2)
    click.secho('\u2713', fg='green')


def _output_analysis(output_folder: PathLike, country: str, data: List[Cases],
                     no_indent: bool, min_confirmed: int, filter_window: int):
    output_folder = pathlib.Path(output_folder)
    analysis_file = output_folder / pathlib.Path(f'{_process_country_name(country)}.json')

    click.echo(f'Writing to {analysis_file}...', nl=False)

    series = TimeSeries(data, 'confirmed', min_confirmed)  # type: ignore
    derivative = analysis.estimate_slope(series, filter_window)
    growth_factor = analysis.growth_factor(series, filter_window)

    entry: Cases
    output = {
        'country': country,
        'date': series.dates,
        'timeseries': [
            {
                'name': 'cases',
                'raw': series._samples,
                'interpolated': analysis.smooth(series, filter_window, False)
            },
            {
                'name': 'dailyChange',
                'raw': series.daily_change,
                'interpolated': np.squeeze(derivative[:, 0]),
                'confidenceInterval': np.squeeze(derivative[:, 1:])
            },
            {
                'name': 'growthFactor',
                'interpolated': np.squeeze(growth_factor[:, 0]),
                'confidenceInterval': np.squeeze(growth_factor[:, 1:])
            }
        ]
    }

    with analysis_file.open('wt') as f:
        args: Dict[str, Any] = {
            'default': _datatype_converter,
        }
        if no_indent is False:
            args['indent'] = 2

        json.dump(output, f, **args)

    click.secho('\u2713', fg='green')


@click.command('analyze')
@click.option('-c', '--country', 'countries', nargs=1, multiple=True,
              help='Specify countries/regions to put into the analysis.')
@click.option('-o', '--output', help='Location of the output files.',
              default='_analysis',
              type=click.Path(dir_okay=True, file_okay=False))
@click.option('--no-indent', is_flag=True, help='Do not indent any JSON output.')
@click.option('--min-confirmed', nargs=1, type=int, default=100, show_default=True,
              help='Remove entries lower that the minimum confirmed number.')
@click.option('--filter-window', nargs=1, type=int, default=14, show_default=True,
              help='Window size when performing least-squares.')
@click.pass_obj
def command(config: dict, countries: Tuple[str], output: str, no_indent: bool,
            min_confirmed: int, filter_window: int):
    '''Generate an analysis from the COVID-19 case numbers.

    The command will perform a series of regression analyses on the COVID-19
    case data.  The results are stored in the specified output folder with one
    JSON file for each country/region.  The 'analysis.json' file lists all of
    the available countries/regions as well as the analysis configuration.
    '''
    click.secho('Generating Report', bold=True)
    click.secho('Regions: ', bold=True, nl=False)

    if len(countries) == 0:
        countries = [None]  # type: ignore
        click.echo('World')
    else:
        click.echo()
        click.echo(',\n'.join(f'  {country}' for country in countries))

    # Set up the input sources.
    input_sources = {
        country: sources.init_source(config['storage'], False, country,
                                     config['sources'])
        for country in countries
    }

    source_info = {
        country: SourceInfo(description=source.details(), url=source.url())
        for country, source in input_sources.items()
    }

    # Populate the database.
    with Storage() as storage:
        for region in countries:
            storage.populate(input_sources[region])

        data = {}
        for region in countries:
            country, province = _parse_region_selector(region)
            data[region] = storage.cases(input_sources[region],
                                         country=country, province=province)

    # Ensure `None` maps to `World` in the dashboard.
    if None in data:
        data['World'] = data[None]  # type: ignore
        del data[None]  # type: ignore

    if None in source_info:
        source_info['World'] = source_info[None]  # type: ignore
        del source_info[None]  # type: ignore

    # Write out the analysis configuration.
    _output_configuration(output, source_info, min_confirmed, filter_window)

    # Process all of the requested countries/regions.
    for country, timeseries in data.items():
        _output_analysis(output, country, timeseries, no_indent, min_confirmed, filter_window)

    click.echo('Generated analysis...' + click.style('\u2713', fg='green'))

import pathlib
from typing import Tuple
import webbrowser

import click

from ._helpers import _parse_region_selector
from .. import sources
from ..dashboard import Dashboard, OutputType
from ..report import SourceInfo
from ..storage import Storage


@click.command('report')
@click.option('-c', '--country', 'countries', nargs=1, multiple=True,
              help='Specify countries/regions to put into the report.')
@click.option('-o', '--output', help='Location of the output file.',
              default='report.html',
              type=click.Path(dir_okay=False, file_okay=True))
@click.option('--min-confirmed', nargs=1, type=int, default=1,
              help='Remove entries lower that the minimum confirmed number.')
@click.option('--filter-window', nargs=1, type=int, default=7,
              help='Window size when performing least-squares.')
@click.option('--no-browser', is_flag=True,
              help='Do not open up the report in a browser.')
@click.option('--dashboard', 'generate_dashboard', is_flag=True,
              help='Generate a dashboard rather that overlaying countries.')
@click.pass_obj
def command(config: dict, countries: Tuple[str], output: str,
            min_confirmed: int, filter_window: int, no_browser: bool,
            generate_dashboard: bool):
    '''Generate a daily COVID-19 report.

    The report is one or more HTML pages with Bokeh-powered plots.  There are a
    few different generation options.  The defaults will output a single,
    aggregate report for all reported world-wide cases into a `report.html`
    file.  It will also open up the report in a browser.
    '''
    click.secho('Generating Report', bold=True)
    click.secho('Regions: ', bold=True, nl=False)

    if len(countries) == 0:
        countries = [None]
        click.echo('World')
    else:
        click.echo(click.style('Regions: ', bold=True) + ','.join(countries))

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

    outpath = pathlib.Path(output).resolve()

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
        data['World'] = data[None]
        del data[None]

    if None in source_info:
        source_info['World'] = source_info[None]
        del source_info[None]

    # Generate the report and/or dashboard.
    click.secho('Dashboard: ', bold=True, nl=False)
    dashboard = Dashboard(output=outpath,
                          sources=source_info,
                          min_confirmed=min_confirmed,
                          filter_window=filter_window)
    if generate_dashboard:
        click.echo('Yes')
        dashboard.output_mode = OutputType.DASHBOARD
    else:
        click.echo('No')
    dashboard.generate(data)

    click.echo('Generated report...' + click.style('\u2713', fg='green'))
    if not no_browser:
        webbrowser.open_new_tab(outpath.as_uri())

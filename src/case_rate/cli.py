import pathlib
from typing import Optional, Tuple
import webbrowser

import click
import toml

from . import filters, sources, VERSION
from .dashboard import Dashboard, OutputType
from .report import SourceInfo
from .storage import Storage


def _parse_region_selector(region: Optional[str]) -> Tuple[Optional[str], Optional[str]]:  # noqa: E501
    '''Parses the region selection format.'''
    if region is None:
        return (None, None)

    parts = region.split(':')
    if len(parts) == 1:
        return (parts[0], None)
    elif len(parts) == 2:
        return (parts[0], parts[1])
    else:
        raise ValueError('Expected "<country>:<province/state>" selector.')


@click.group()
@click.option('-c', '--config', 'config_path', default='case-rate.toml',
              type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='configuration file', show_default=True)
@click.pass_context
def main(ctx: click.Context, config_path):
    '''Process case rate data for COVID-19.'''
    config_path = pathlib.Path(config_path)
    with config_path.open() as f:
        config = toml.load(f)

    # Ensure there's a place to store downloaded data.
    storage = pathlib.Path(config['case-rate']['storage'])
    if not storage.exists():
        storage.mkdir(parents=True)

    # Prepare the context sent to the subcommands.
    ctx.ensure_object(dict)
    ctx.obj['storage'] = storage
    ctx.obj['database'] = config['case-rate']['database']
    ctx.obj['sources'] = config['sources']

    # Print the preamble (common to all commands).
    click.secho(f'COVID-19 Case Rates (v{VERSION})', bold=True)
    click.secho('--', bold=True)


@main.command('sources')
@click.argument('action', type=click.Choice(['list', 'update']))
@click.pass_obj
def manage_sources(config: dict, action: str):
    '''Perform simple management operations on the input data sources.

    The two main actions are:

    'list'   - display all of the available data sources

    'update' - batch update all of the data sources
    '''
    def to_selector(country, region):
        if region is None:
            if country is None:
                return None
            else:
                return country
        else:
            return ':'.join((country, region))

    regions = {key: to_selector(*key) for key in sources.DATA_SOURCES.keys()}

    if action == 'list':
        click.secho('Available Sources:', bold=True)
    elif action == 'update':
        click.secho('Updating Sources: ', bold=True)

    for key, SourceCls in sources.DATA_SOURCES.items():
        if action == 'list':
            click.echo(f'  Name: {SourceCls.name()}')
            click.echo(f'  Description: {SourceCls.details()}')
        elif action == 'update':
            click.echo(f'- Updating {SourceCls.name()}')
            sources.init_source(config['storage'], True, regions[key],
                                config['sources'])
        click.echo('  --')


@main.command()
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
def report(config: dict, countries: Tuple[str], output: str,
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


@main.command()
@click.option('-c', '--country', nargs=1,
              help='Select reports for a single country.')
@click.option('--details', is_flag=True, help='Show the full report table.')
@click.pass_obj
def info(config: dict, country: Optional[str], details: bool):
    '''Get information about the contents of the COVID-19 data set.

    This will produce some general informattion about the data set or, if
    specified, the particular country.
    '''
    input_source = sources.init_source(config['storage'], False, country,
                                       config['sources'])

    country, province = _parse_region_selector(country)

    with Storage() as storage:
        storage.populate(input_source)
        cases = storage.cases(input_source, country=country, province=province)

    cases = filters.sum_by_date(cases)

    click.echo(click.style('Input Source: ', bold=True) + input_source.details())  # noqa: E501
    click.echo(click.style('Available Reports: ', bold=True) + str(len(cases)))

    if country is not None:
        click.echo(click.style('Country: ', bold=True) + country)

    click.echo(f'First: {cases[0].date}')
    click.echo(f'  - Confirmed: {cases[0].confirmed}')
    click.echo(f'  - Recovered: {cases[0].resolved}')
    click.echo(f'  - Deceased:  {cases[0].deceased}')
    click.echo(f'Last:  {cases[-1].date}')
    click.echo(f'  - Confirmed: {cases[-1].confirmed}')
    click.echo(f'  - Recovered: {cases[-1].resolved}')
    click.echo(f'  - Deceased:  {cases[-1].deceased}')

    if details:
        click.secho('Reporting: ', bold=True)
        click.echo('{:>10} {:>10} {:>10}'.format('Date',
                                                 'Confirmed',
                                                 'Deaths'))
        for case in cases:
            click.echo('{:10} {:10} {:10}'.format(str(case.date),
                                                  case.confirmed,
                                                  case.deceased))


if __name__ == '__main__':
    main()

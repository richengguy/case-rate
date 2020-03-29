import pathlib
from typing import Optional, Tuple
import webbrowser

import click
import matplotlib.pyplot as plt
import numpy as np

from case_rate.dashboard import Dashboard, OutputType
from case_rate.dataset import DataSource, ConfirmedCases
from case_rate.timeseries import TimeSeries


def preamble(ctx: click.Context):
    '''Print the command preamble.'''
    click.secho('COVID-19 Case Rates', bold=True)
    click.secho('--', bold=True)
    click.secho('Dataset Path: ', bold=True, nl=False)
    click.echo(ctx.obj['DATASET_PATH'])


@click.group()
@click.option('-d', '--dataset',
              type=click.Path(file_okay=False, dir_okay=True),
              help='Dataset storage path.',
              default='./covid19_repo', show_default=True)
@click.pass_context
def main(ctx: click.Context, dataset):
    '''Process case rate data for COVID-19.'''
    ctx.ensure_object(dict)
    ctx.obj['DATASET_PATH'] = pathlib.Path(dataset)


@main.command()
@click.option('-r', '--repo', type=click.STRING, metavar='GIT_URL',
              help='Path to the CSSE COVID-19 repo.',
              default='https://github.com/CSSEGISandData/COVID-19.git',
              show_default=True)
@click.pass_context
def download(ctx: click.Context, repo):
    '''Download the latest COVID-19 data from the JHU CSSE repository.

    This will do one of two things:

        1) Clone the COVID-19 repo if it does not yet exist; or

        2) Check out the latest 'master'.

    By default, it accesses the 'CSSEGISandData/COVID-19' GitHub repo.  An
    alternate repo can be specified with the '-r' flag.
    '''
    preamble(ctx)
    if ctx.obj['DATASET_PATH'].exists():
        DataSource.update(ctx.obj['DATASET_PATH'])
    else:
        DataSource.create(repo, ctx.obj['DATASET_PATH'])


@main.command()
@click.option('-c', '--country', 'countries', nargs=1, multiple=True,
              help='Specify countries/regions to put into the report.')
@click.option('-o', '--output', help='Location of the output file.',
              default='report.html',
              type=click.Path(dir_okay=False, file_okay=True))
@click.option('--no-browser', is_flag=True,
              help='Do not open up the report in a browser.')
@click.option('--dashboard', 'generate_dashboard', is_flag=True,
              help='Generate a dashboard rather that overlaying countries.')
@click.pass_context
def report(ctx: click.Context, countries: Tuple[str], output: str,
           no_browser: bool, generate_dashboard: bool):
    '''Generate a daily COVID-19 report.

    The report is one or more HTML pages with Bokeh-powered plots.  There are a
    few different generation options.  The defaults will output a single,
    aggregate report for all reported world-wide cases into a `report.html`
    file.  It will also open up the report in a browser.
    '''
    preamble(ctx)
    outpath = pathlib.Path(output).resolve()
    dataset = DataSource(ctx.obj['DATASET_PATH'])
    cases = dataset.cases

    click.echo(click.style('Output: ', bold=True) + outpath.as_posix())
    click.secho('Region(s): ', bold=True, nl=False)
    if len(countries) == 0:
        click.echo('World')
        data = {'World': cases}
    else:
        click.echo(', '.join(countries))
        data = {country: cases.for_country(country) for country in countries}

    click.secho('Dashboard: ', bold=True, nl=False)
    dashboard = Dashboard(output=outpath, source=dataset.github_link)
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
@click.pass_context
def info(ctx: click.Context, country: Optional[str], details: bool):
    '''Get information about the contents of the COVID-19 data set.

    This will produce some general informattion about the data set or, if
    specified, the particular country.
    '''
    preamble(ctx)
    dataset = DataSource(ctx.obj['DATASET_PATH'])
    reports = dataset.cases

    if country is not None:
        reports = reports.for_country(country)

    click.secho('Available Reports: ', bold=True, nl=False)
    click.echo(len(reports))

    if country is not None:
        click.secho('Country: ', bold=True, nl=False)
        click.echo(country)

    click.echo('First: {}-{:02}-{:02}'.format(*(reports.dates[0])))
    click.echo('  - Confirmed: {}'.format(reports.reports[0].total_confirmed))
    click.echo('  - Deaths:    {}'.format(reports.reports[0].total_deaths))
    click.echo('Last:  {}-{:02}-{:02}'.format(*(reports.dates[-1])))
    click.echo('  - Confirmed: {}'.format(reports.reports[-1].total_confirmed))
    click.echo('  - Deaths:    {}'.format(reports.reports[-1].total_deaths))

    if details:
        click.secho('Reporting:', bold=True)
        click.echo('{:>10} {:>10} {:>10}'.format('Date', 'Confirmed', 'Deaths'))  # noqa: E501
        timeseries = TimeSeries(reports)
        for date, (confirmed, deaths) in zip(timeseries.dates, timeseries.as_list()):  # noqa: E501
            click.echo('{:10} {:10} {:10}'.format(str(date), confirmed, deaths))  # noqa: E501


if __name__ == '__main__':
    main()

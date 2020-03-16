import pathlib
from typing import Optional, Tuple

import click
import matplotlib.pyplot as plt

from case_rate import Dataset, ReportSet, TimeSeries


@click.group()
@click.option('-d', '--dataset',
              type=click.Path(file_okay=False, dir_okay=True),
              help='Dataset storage path.',
              default='./covid19_repo', show_default=True)
@click.pass_context
def main(ctx: click.Context, dataset):
    '''Process case rate data for COVID-19.'''
    click.secho('COVID-19 Case Rates', bold=True)
    click.secho('--', bold=True)
    ctx.ensure_object(dict)
    ctx.obj['DATASET_PATH'] = pathlib.Path(dataset)

    click.secho('Dataset Path: ', bold=True, nl=False)
    click.echo(ctx.obj['DATASET_PATH'])


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
    if ctx.obj['DATASET_PATH'].exists():
        Dataset.update(ctx.obj['DATASET_PATH'])
    else:
        Dataset.create(repo, ctx.obj['DATASET_PATH'])


@main.command()
@click.option('-c', '--country', nargs=1,
              help='Select reports for a single country.')
@click.option('--details', is_flag=True, help='Show the full report table.')
@click.pass_context
def info(ctx: click.Context, country: Optional[str], details: bool):
    '''Get information about the contents of the COVID-19 data set.'''
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    reports = dataset.reports

    if country is not None:
        reports = reports.for_country(country)

    click.secho('Available Reports: ', bold=True, nl=False)
    click.echo(len(reports))

    if country is not None:
        click.secho('Country: ', bold=True, nl=False)
        click.echo(country)

    click.echo('First: {}-{:02}-{:02}'.format(*(reports.dates[0])))
    click.echo('  - Confirmed: {}'.format(reports.reports[0].total_confirmed))
    click.echo('  - Recovered: {}'.format(reports.reports[0].total_recovered))
    click.echo('Last:  {}-{:02}-{:02}'.format(*(reports.dates[-1])))
    click.echo('  - Confirmed: {}'.format(reports.reports[-1].total_confirmed))
    click.echo('  - Recovered: {}'.format(reports.reports[-1].total_recovered))

    if details:
        click.secho('Reporting:', bold=True)
        click.echo('{:>10} {:>10} {:>10} {:>10}'.format('Date', 'Confirmed', 'Deaths', 'Resolved'))  # noqa: E501
        timeseries = TimeSeries(reports)
        for date, (confirmed, deaths, resolved) in zip(timeseries.dates, timeseries.as_list()):  # noqa: E501
            click.echo('{:10} {:10} {:10} {:10}'.format(str(date), confirmed, deaths, resolved))  # noqa: E501


@main.command()
@click.option('-c', '--country', 'countries', nargs=1, multiple=True,
              help='Plot results for a single country.')
@click.pass_context
def plot(ctx: click.Context, countries: Tuple[str]):
    '''Generates plots from the downloaded COVID-19 data.'''
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    click.secho('Plotting: ', bold=True, nl=False)

    def plot_confirmed(reports: ReportSet, name: str):
        timeseries = TimeSeries(reports)
        plt.semilogy(timeseries.dates, timeseries.confirmed, label=name)

    if len(countries) == 0:
        click.echo('all reports')
        plot_confirmed(dataset.reports, 'all')
    else:
        click.echo(', '.join(countries))
        for country in countries:
            plot_confirmed(dataset.for_country(country), country)

    plt.title('COVID-19 Cases')
    plt.xlabel('Date')
    plt.ylabel('Confirmed')
    plt.legend()
    plt.xticks(rotation=30)

    plt.show()


if __name__ == '__main__':
    main()

import pathlib
from typing import Optional, Tuple

import click
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from case_rate import Dataset, ReportSet, TimeSeries


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
        Dataset.update(ctx.obj['DATASET_PATH'])
    else:
        Dataset.create(repo, ctx.obj['DATASET_PATH'])


@main.command()
@click.option('-c', '--country', nargs=1,
              help='Select reports for a single country.')
@click.option('--details', is_flag=True, help='Show the full report table.')
@click.pass_context
def info(ctx: click.Context, country: Optional[str], details: bool):
    '''Get information about the contents of the COVID-19 data set.

    This will prodcue some general informattion about the data set or, if
    specified, the particular country.
    '''
    preamble(ctx)
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
    '''Generates plots from the downloaded COVID-19 data.

    This will generate plots for the confirmed cases along a semi-log y-axis.
    '''
    preamble(ctx)
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    click.secho('Plotting: ', bold=True, nl=False)

    def plot_confirmed(reports: ReportSet, name: str):
        timeseries = TimeSeries(reports)
        _, filtered = timeseries.growth_factor(return_filtered=True)
        plt.semilogy(timeseries.dates, filtered, label=name)
        plt.semilogy(timeseries.dates, timeseries.confirmed,
                     color='gray', alpha=0.5)
        plt.annotate(timeseries.confirmed[-1],
                     (timeseries.dates[-1], timeseries.confirmed[-1]))

    def plot_growth_factor(timeseries: TimeSeries, name: str):
        rates = timeseries.growth_factor()
        plt.plot(timeseries.dates, rates[:, 0], label=name)
        plt.fill_between(timeseries.dates, rates[:, 1], rates[:, 2], alpha=0.4)

    def plot_daily_cases(timeseries: TimeSeries, name: str):
        new_cases = timeseries.daily_new_cases()
        plt.bar(timeseries.dates, new_cases, label=name)

    # Confirmed Cases
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

    # Growth Factors
    plt.figure()
    if len(countries) == 0:
        timeseries = TimeSeries(dataset.reports)
        xmin = timeseries.dates[0]
        xmax = timeseries.dates[-1]
        plot_growth_factor(timeseries, 'all')
    else:
        xmin = None  # type: ignore
        xmax = None  # type: ignore
        for country in countries:
            timeseries = TimeSeries(dataset.for_country(country))
            if xmin is None:
                xmin = timeseries.dates[0]
                xmax = timeseries.dates[-1]
            else:
                xmin = min(xmin, timeseries.dates[0])
                xmax = max(xmax, timeseries.dates[-1])

            plot_growth_factor(timeseries, country)

    plt.title('COVID-19 Growth Factor')
    plt.xlabel('Date')
    plt.ylabel('Growth Factor')
    plt.hlines(y=1, xmin=xmin, xmax=xmax, linestyles='dashed', alpha=0.8)
    plt.legend()
    plt.xticks(rotation=30)

    # Daily New Cases
    plt.figure()
    if len(countries) == 0:
        timeseries = TimeSeries(dataset.reports)
        plot_daily_cases(timeseries, 'all')
    else:
        xmin = None  # type: ignore
        xmax = None  # type: ignore
        for country in countries:
            timeseries = TimeSeries(dataset.for_country(country))
            plot_daily_cases(timeseries, country)

    plt.title('COVID-19 Daily New Cases')
    plt.xlabel('Date')
    plt.ylabel('New Cases')
    plt.legend()
    plt.xticks(rotation=30)

    plt.show()


@main.command()
@click.argument('first', metavar='COUNTRY', nargs=1)
@click.argument('second', metavar='COUNTRY', nargs=1)
@click.pass_context
def compare(ctx: click.Context, first: str, second: str):
    '''Compare the 'confirmed' curves of two countries.

    Assuming that the epidemiological curves are logistic (i.e. sigmoidal),
    then the two curves are log-linear during the exponential growth phase.
    This means that the normalized cross-correlation between the curves
    provides two pieces of information:

     - Whether or not one curve is leading or lagging the other, as given by
       the point in time where the cross-correlation is at a maximum.

     - The similarity between the two curves, where a value closer to '1' means
       that the two curves are more similar.

    The lower the maximum cross-correlation score, the less similar the two
    curves are, which can indicate a divergence.
    '''
    preamble(ctx)
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    click.secho('Comparing: ', bold=True, nl=False)
    click.echo(f"{first} {second}")

    countryA = TimeSeries(dataset.for_country(first))
    countryB = TimeSeries(dataset.for_country(second))

    # Compute the cross-correlation between two countries.
    xcorr = TimeSeries.crosscorrelate(countryA, countryB)
    ind = np.argmax(xcorr[:, 1])
    click.secho('Maximum Lag: ', bold=True, nl=False)
    click.echo(f'{xcorr[ind, 0]} days')

    fig = plt.figure()
    gs = gridspec.GridSpec(2, 2)

    ax = fig.add_subplot(gs[0, 0])
    ax.plot(countryA.dates, countryA.confirmed, label=first)
    ax.plot(countryB.dates, countryB.confirmed, label=second)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cases')
    ax.set_title(f'{first}/{second} Confirmed')
    plt.setp(ax.get_xticklabels(), rotation=30)

    ax = fig.add_subplot(gs[0, 1])
    ax.semilogy(countryA.dates, countryA.confirmed, label=first)
    ax.semilogy(countryB.dates, countryB.confirmed, label=second)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cases')
    ax.set_title(f'{first}/{second} Confirmed (Log-scale)')
    plt.setp(ax.get_xticklabels(), rotation=30)

    ax = fig.add_subplot(gs[1, :])
    ax.plot(xcorr[:, 0], xcorr[:, 1])
    ax.plot(xcorr[ind, 0], xcorr[ind, 1], 'x')
    ax.vlines(x=xcorr[ind, 0], ymin=0, ymax=xcorr[ind, 1])
    ax.set_xlabel(f'Lag (Days); max @ {xcorr[ind, 0]}')
    ax.set_ylabel('Correlation Coefficient')

    plt.show()


if __name__ == '__main__':
    main()

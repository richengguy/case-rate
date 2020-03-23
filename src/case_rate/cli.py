import pathlib
from typing import Optional, Tuple

import click
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from case_rate import Dataset, ReportSet, TimeSeries
from case_rate.report import HTMLReport


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
@click.option('-c', '--country', 'countries', nargs=1, multiple=True,
              help='Specify countries/regions to put into the report.')
@click.option('-o', '--output', help='Location of the output file.',
              default='report.html',
              type=click.Path(dir_okay=False, file_okay=True))
@click.pass_context
def report(ctx: click.Context, countries: Tuple[str], output: str):
    '''Generate a daily COVID-19 report.'''
    preamble(ctx)
    dataset = Dataset(ctx.obj['DATASET_PATH'])

    if len(countries) == 0:
        data = {'World': TimeSeries(dataset.reports)}
    else:
        data = {
            country: TimeSeries(dataset.for_country(country))
            for country in countries
        }

    click.echo(click.style('Output: ', bold=True) + output)
    report = HTMLReport()
    html = report.generate_report(data, dataset.github_link)

    with open(output, 'w') as f:
        f.write(html)

    click.echo('Generated report...' + click.style('\u2713', fg='green'))


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
def plot(ctx: click.Context, countries):
    '''Generates plots from the downloaded COVID-19 data.

    This will generate plots for the confirmed cases along a semi-log y-axis.
    '''
    def plot_confirmed(reports: ReportSet, name: str):
        timeseries = TimeSeries(reports)
        filtered = timeseries.smoothed
        plt.semilogy(timeseries.dates, filtered, label=name)
        plt.semilogy(timeseries.dates, timeseries.confirmed,
                     color='gray', alpha=0.5)
        plt.annotate(timeseries.confirmed[-1],
                     (timeseries.dates[-1], timeseries.confirmed[-1]))

    def plot_growth_factor(timeseries: TimeSeries, name: str):
        rates = timeseries.growth_factor()
        plt.plot(timeseries.dates, rates[:, 0], label=name)
        plt.fill_between(timeseries.dates, rates[:, 1], rates[:, 2], alpha=0.4)

    def plot_log_slope(timeseries: TimeSeries, name: str):
        rates = timeseries.log_slope()
        rates = np.power(10, rates)
        plt.plot(timeseries.dates, rates[:, 0], label=name)
        plt.fill_between(timeseries.dates, rates[:, 1], rates[:, 2], alpha=0.4)

    def plot_daily_cases(timeseries: TimeSeries, name: str):
        new_cases = timeseries.daily_new_cases()
        smoothed = timeseries.daily_new_cases(True)
        plt.bar(timeseries.dates, new_cases, alpha=0.4)
        plt.plot(timeseries.dates, smoothed, label=name)

    preamble(ctx)
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    click.secho('Plotting: ', bold=True, nl=False)

    # Sort countries from highest to lowest in count.
    countries = sorted(
        countries,
        key=lambda country: dataset.for_country(country).reports[-1].total_confirmed  # noqa: E501
    )
    countries.reverse()

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
    plt.ylim((0, 4))
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

    # Log-slope estimate
    plt.figure()
    if len(countries) == 0:
        timeseries = TimeSeries(dataset.reports)
        plot_log_slope(timeseries, 'all')
    else:
        xmin = None  # type: ignore
        xmax = None  # type: ignore
        for country in countries:
            timeseries = TimeSeries(dataset.for_country(country))
            plot_log_slope(timeseries, country)

    plt.title('COVID-19 Daily Multiplier')
    plt.xlabel('Date')
    plt.ylabel('Multiplier')
    plt.ylim(1, plt.ylim()[1])
    plt.legend()
    plt.xticks(rotation=30)

    plt.show()


@main.command()
@click.argument('first', metavar='COUNTRY', nargs=1)
@click.argument('second', metavar='COUNTRY', nargs=1)
@click.pass_context
def compare(ctx: click.Context, first: str, second: str):
    '''Compare the 'confirmed' curves of two countries.'''
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
    gs = gridspec.GridSpec(1, 2)

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

    confA = np.array(countryA.confirmed)
    confB = np.array(countryB.confirmed)

    if len(confA) < len(confB):
        confB = confB[(len(confB) - len(confA)):]
        dates = countryA.dates
    else:
        confA = confA[(len(confA) - len(confB)):]
        dates = countryB.dates

    plt.figure()
    plt.plot(dates, np.exp(np.log(confA) - np.log(confB)))
    plt.title(f'Relative Cases Between {first} and {second}.')
    plt.xticks(rotation=30)
    plt.xlabel('Date')
    plt.ylabel('Multiplier')

    plt.show()


if __name__ == '__main__':
    main()

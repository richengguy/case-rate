from typing import Optional

import click

from ._helpers import _parse_region_selector
from .. import filters
from .. import sources
from ..storage import Storage


@click.command('info')
@click.option('-c', '--country', nargs=1,
              help='Select reports for a single country.')
@click.option('--details', is_flag=True, help='Show the full report table.')
@click.pass_obj
def command(config: dict, country: Optional[str], details: bool):
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
    if province is not None:
        click.echo(click.style('Province/State: ', bold=True) + province)

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
        click.echo('{:>10} {:>10} {:>10} {:>10}'.format('Date',
                                                        'Confirmed',
                                                        'Recovered',
                                                        'Deaths'))
        for case in cases:
            click.echo('{:10} {:10} {:10} {:10}'.format(str(case.date),
                                                        case.confirmed,
                                                        case.resolved,
                                                        case.deceased))

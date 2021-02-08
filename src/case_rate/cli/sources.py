import click

from .. import sources
from ..storage import InputSource


@click.command('sources')
@click.argument('action', type=click.Choice(['list', 'update']))
@click.pass_obj
def command(config: dict, action: str):
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

    SourceCls: InputSource
    for key, SourceCls in sources.DATA_SOURCES.items():  # type: ignore
        if action == 'list':
            click.echo(f'  Name: {SourceCls.name()}')
            click.echo(f'  Description: {SourceCls.details()}')
        elif action == 'update':
            click.echo(f'- Updating {SourceCls.name()}')
            sources.init_source(config['storage'], True, regions[key],
                                config['sources'])
        click.echo('  --')

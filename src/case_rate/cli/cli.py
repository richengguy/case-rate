import pathlib

import click
import toml

from . import analyze, info, sources
from .. import VERSION


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


main.add_command(analyze.command)
main.add_command(info.command)
main.add_command(sources.command)


if __name__ == '__main__':
    main()

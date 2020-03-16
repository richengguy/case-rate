import pathlib

import click

from case_rate.dataset import Dataset


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
@click.pass_context
def info(ctx: click.Context):
    '''Get information about the contents of the COVID-19 data set.'''
    dataset = Dataset(ctx.obj['DATASET_PATH'])
    click.secho('Daily Reports: ', bold=True, nl='')
    click.echo(len(dataset.reports))
    click.echo('  - First: {}-{:02}-{:02}'.format(*(dataset.reports.dates[0])))
    click.echo('  - Last:  {}-{:02}-{:02}'.format(*(dataset.reports.dates[-1])))


@main.command()
@click.pass_context
def plot(ctx: click.Context):
    '''Generates plots from the downloaded COVID-19 data.'''
    dataset = Dataset(ctx.obj['DATASET_PATH'])


if __name__ == '__main__':
    main()

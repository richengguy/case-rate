import pathlib

import click

from case_rate.dataset import Dataset


@click.group()
def main():
    '''Process case rate data for COVID-19.'''
    click.secho('COVID-19 Case Rates', bold=True)
    click.secho('--', bold=True)


@main.command()
@click.option('-r', '--repo', type=click.STRING, metavar='GIT_URL',
              help='Path to the CSSE COVID-19 repo.',
              default='https://github.com/CSSEGISandData/COVID-19.git',
              show_default=True)
@click.option('-o', '--output',
              type=click.Path(file_okay=False, dir_okay=True),
              help='Repository storage path.',
              default='./covid19_repo', show_default=True)
def download(repo, output):
    '''Download the latest COVID-19 data from the JHU CSSE repository.

    This will do one of two things:

        1) Clone the COVID-19 repo if it does not yet exist; or

        2) Check out the latest 'master'.

    By default, it accesses the 'CSSEGISandData/COVID-19' GitHub repo.  An
    alternate repo can be specified with the '-r' flag.
    '''
    output = pathlib.Path(output)
    if output.exists():
        Dataset.update(output)
    else:
        Dataset.create(repo, output)


@main.command()
def plot():
    '''Generates plots from the downloaded COVID-19 data.'''


if __name__ == '__main__':
    main()

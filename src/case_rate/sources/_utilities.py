import pathlib

import click
import requests


FILE_SIZE_LIMIT = 10  # 10 Mb


def download_file(url: str, filename: pathlib.Path):
    '''Retrieve the contents at the specified URL and save it to disk.

    Parameters
    ----------
    url : str
        URL to retrieve
    filename : path
        path to where the file will be stored
    '''
    click.echo(f'Downloading {url}')
    response = requests.get(url)
    nbytes = len(response.content)
    if nbytes > FILE_SIZE_LIMIT*2**20:
        raise ValueError(
            f'Server response was larger than {FILE_SIZE_LIMIT} Mb {nbytes}; '
            'something is off with the source.')

    with filename.open('w') as f:
        f.write(response.text)

    click.echo(click.style('\u2713', fg='green', bold=True) +
               f'...saved to `{filename}`')

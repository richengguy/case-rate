import pathlib
import subprocess

import click


def _git(*args, cwd: pathlib.Path = None):
    '''Run a git command using subprocess.

    This will just call the system's own 'git'.  For example, calling this with
    the arguments ``_git('clone', 'https://github.com/user/repo.git')`` is
    functionally the same as ``$ git clone https://github.com/user/repo.git``.

    Parameters
    ----------
    cwd: pathlib.Path
        the current working directory when running the 'git' command
    '''
    cmd = ['git'] + list(args)
    output = subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)
    click.echo(output.stdout)
    click.echo(output.stderr)


class Dataset(object):
    '''Represents the contents of a time-series dataset.'''
    def __init__(self, path: pathlib.Path):
        '''
        Parameters
        ----------
        path : pathlib.Path
            path to where the dataset CSV files are stored
        '''
        click.echo(f'Opening repo at "{path}".')

    @staticmethod
    def create(repo: str, path: pathlib.Path) -> 'Dataset':
        '''Creates a dataset at the given path.

        This will check out the git repo and clone it to the specified folder.

        Parameters
        ----------
        repo : str
            URL to the git repo with the dataset
        path : pathlib.Path
            path to where the dataset repo is located

        Returns
        -------
        Dataset
            an initialized ``Dataset`` object
        '''
        click.echo(f'Cloning "{repo}" to "{path}"')
        _git('clone', repo, path.as_posix())
        return Dataset(path)

    @staticmethod
    def update(path: pathlib.Path) -> 'Dataset':
        '''Update an existing data set at the specified path.

        Parameters
        ----------
        path: pathlib.Path
            path to the COVID-19 dataset repo

        Returns
        -------
        Dataset
            an initialized ``Dataset`` object
        '''
        click.echo(f'Updating COVID-19 dataset at "{path}".')
        _git('pull', cwd=path)
        return Dataset(path)

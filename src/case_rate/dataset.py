from collections import OrderedDict
import csv
import pathlib
import subprocess
from typing import List, Tuple

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


def _parse_name(csvfile: pathlib.Path) -> Tuple[int, int, int]:
        '''Parse the month-day-year file name format.

        Parameters
        ----------
        csvfile : pathlib.Path
            path to one of the daily report CSV files

        Returns
        -------
        Tuple[int, int, int]
            a ``(year, month, day)`` tuple
        '''
        name = csvfile.stem
        parts = name.split('-')
        return int(parts[2]), int(parts[0]), int(parts[1])


class DailyReport(object):
    '''Represents the contents of a single "daily report" CSV file.'''
    def __init__(self, path: pathlib.Path):
        '''
        Parameters
        ----------
        path : pathlib.Path
            path to the report CSV file
        '''


class ReportCollection(object):
    '''A collection of JHU CSSE daily report CSV files.

    This provides a simple mechanism to represent the contents of the
    repository.

    Attributes
    ----------
    dates: list of ``(year, month, day)``
        a list of all available dates within the report collection
    '''
    def __init__(self, path: pathlib.Path):
        '''
        Parameters
        ----------
        path : pathlib.Path
            path to the reports folder
        '''
        files = path.glob('*.csv')

        reports = []
        for csvfile in files:
            date = _parse_name(csvfile)
            reports.append((date, DailyReport(csvfile)))

        reports.sort(key=lambda entry: entry[0][2])  # sort by day
        reports.sort(key=lambda entry: entry[0][1])  # sort by month
        reports.sort(key=lambda entry: entry[0][0])  # sort by year

        self._reports = OrderedDict(reports)

    def __len__(self):
        return len(self._reports)

    @property
    def dates(self) -> List[Tuple[int, int, int]]:
        return list(self._reports.keys())


class Dataset(object):
    '''Represents the contents of a time-series dataset.

    Attributes
    ----------
    reports: ReportsCollection
        the collection of available daily reports
    '''
    DATA = pathlib.PurePath('csse_covid_19_data')
    DAILY_REPORTS = DATA / pathlib.PurePath('csse_covid_19_daily_reports')

    def __init__(self, path: pathlib.Path):
        '''
        Parameters
        ----------
        path : pathlib.Path
            path to where the dataset CSV files are stored
        '''
        if not path.exists():
            raise ValueError(f'{path} does not exist.')
        self._reports = ReportCollection(path / Dataset.DAILY_REPORTS)

    @property
    def reports(self):
        return self._reports

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

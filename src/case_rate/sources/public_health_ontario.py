import csv
import datetime
import pathlib
from typing import Generator

import click
import requests

from case_rate._types import Cases, CaseTesting, PathLike
from case_rate.storage import InputSource


def _download(url: str, filename: pathlib.Path):
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
    if nbytes > 2**20:
        raise ValueError(
            f'Server response was larger than 1 Mb {nbytes}; '
            'something is off with the source.')

    with filename.open('w') as f:
        f.write(response.text)

    click.echo(click.style('\u2713', fg='green', bold=True) +
               f'...saved to `{filename}`')


def _to_date(date: str) -> datetime.date:
    '''Converts a date string into a date object.

    Parameters
    ----------
    date : str
        input date string of the form "YYYY-MM-DD"

    Returns
    -------
    datetime.date
        output ``date`` object
    '''
    dt = datetime.datetime.strptime(date, '%Y-%m-%d')
    return dt.date()


def _to_int(number: str) -> int:
    '''Converts a numerical string into an integer.

    This performs an extra check to see if the input string is ``''``.  This is
    then treated as a zero.  Anything else will result in a ``ValueError``.

    Parameters
    ----------
    number : str
        input string as a number

    Returns
    -------
    int
        the string's integer value

    Throws
    ------
    :exc:`ValueError`
        if the string is not actually a number
    '''
    if len(number) == 0:
        return 0

    if number == 'N/A':
        return 0

    try:
        count = int(number)
    except ValueError:
        count = int(float(number))

    return count


class PublicHealthOntarioSource(InputSource):
    '''Uses reporting data published by Public Health Ontario.

    Public Health Ontario (PHO) publicizes its data via the Government of
    Ontario's Data Catalogue.  The `Status of COVID-19 cases in Ontario`_
    contains the original source data along with an API to access it.  This
    downloads the full CSV to simplify the implementation.

    .. _Status of COVID-19 cases in Ontario: https://data.ontario.ca/dataset/status-of-covid-19-cases-in-ontario
    '''  # noqa: E501
    def __init__(self, path: PathLike, url: str = None,
                 info: str = None, update: bool = True):
        '''
        Parameters
        ----------
        path : path-like object
            the path (on disk) where the CSV file is located
        url : str
            the URL to PHO's COVID-19 report
        info : str optional
            the URL to the main information path (not the CSV file); not
            provided then it uses the default link
        update : bool, optional
            if ``True`` then updates an existing CSV file to the latest version
        '''
        if url is None:
            raise ValueError('Missing data source URL.')
        if info is None:
            raise ValueError('Missing information URL.')

        path = pathlib.Path(path) / 'covid19.csv'
        if path.exists():
            if update:
                click.echo('Updating PHO "Status of COVID-19 cases in Ontario" report.')  # noqa: E501
                _download(url, path)
        else:
            click.echo('Accessing PHO "Status of COVID-19 cases in Ontario" report.')  # noqa: E501
            _download(url, path)

        self._info = info
        self._path = path

    @classmethod
    def name(cls) -> str:
        return 'public-health-ontario'

    @classmethod
    def details(cls) -> str:
        return 'Public Health Ontario - Status of COVID-19 cases in Ontario'

    def url(self) -> str:
        return self._info

    def cases(self) -> Generator[Cases, None, None]:
        with self._path.open() as f:
            contents = csv.DictReader(f)
            for entry in contents:
                yield Cases(
                    date=_to_date(entry['Reported Date']),
                    province='Ontario',
                    country='Canada',
                    confirmed=_to_int(entry['Total Cases']),
                    resolved=_to_int(entry['Resolved']),
                    deceased=_to_int(entry['Deaths'])
                )

    def testing(self) -> Generator[CaseTesting, None, None]:
        with self._path.open() as f:
            contents = csv.DictReader(f)
            for entry in contents:
                yield CaseTesting(
                    date=_to_date(entry['Reported Date']),
                    province='Ontario',
                    country='Canada',
                    tested=_to_int(entry['Total tests completed in the last day']),  # noqa: E501
                    under_investigation=_to_int(entry['Under Investigation'])
                )

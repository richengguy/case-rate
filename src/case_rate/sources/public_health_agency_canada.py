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
        input date string of the form "DD-MM-YYYY"

    Returns
    -------
    datetime.date
        output ``date`` object
    '''
    dt = datetime.datetime.strptime(date, '%d-%m-%Y')
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

    return int(number)


class PublicHealthAgencyCanadaSource(InputSource):
    '''Uses reporting data published by the PHAC.

    This input source uses a CSV file that's regularly updated by the Public
    Health Agency of Canada (PHAC).  The default source is
    https://health-infobase.canada.ca/src/data/covidLive/covid19.csv.  The
    data source will link back to the original PHAC site rather than to the
    file.
    '''
    def __init__(self, path: PathLike, url: str, info: str,
                 update: bool = True):
        '''
        Parameters
        ----------
        path : path-like object
            the path (on disk) where the CSV file is located
        url : str
            the URL to the Government of Canada's COVID-19 report
        info : str optional
            the URL to the main information path (not the CSV file)
        update : bool, optional
            if ``True`` then updates an existing CSV file to the latest version
        '''
        path = pathlib.Path(path) / 'covid19.csv'
        if path.exists():
            if update:
                click.echo('Updating PHAC COVID-19 report.')
                _download(url, path)
        else:
            click.echo('Accessing PHAC COVID-19 report.')
            _download(url, path)

        self._info = info
        self._path = path

    @classmethod
    def name(cls) -> str:
        return 'public-health-agency-canada'

    @classmethod
    def details(cls) -> str:
        return 'Public Health Agency of Canada - Current Situation'

    def url(self) -> str:
        return self._info

    def cases(self) -> Generator[Cases, None, None]:
        with self._path.open() as f:
            contents = csv.DictReader(f)
            for entry in contents:
                if entry['prname'] == 'Canada':
                    continue

                yield Cases(
                    date=_to_date(entry['date']),
                    province=entry['prname'],
                    country='Canada',
                    confirmed=_to_int(entry['numtotal']),
                    resolved=_to_int(entry['numrecover']),
                    deceased=_to_int(entry['numdeaths'])
                )

    def testing(self) -> Generator[CaseTesting, None, None]:
        with self._path.open() as f:
            contents = csv.DictReader(f)
            for entry in contents:
                if entry['prname'] == 'Canada':
                    continue

                yield CaseTesting(
                    date=_to_date(entry['date']),
                    province=entry['prname'],
                    country='Canada',
                    tested=_to_int(entry['numtested']),
                    under_investigation=-1
                )

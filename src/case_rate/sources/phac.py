import csv
import datetime
import pathlib
from typing import Generator, Optional

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


class PHACSource(InputSource):
    '''Uses reporting data published by the PHAC.

    This input source uses a CSV file that's regularly updated by the Public
    Health Agency of Canada (PHAC).  The default source is
    https://health-infobase.canada.ca/src/data/covidLive/covid19.csv.  The
    data source will link back to the original PHAC site rather than to the
    file.
    '''
    CSV_URL = 'https://health-infobase.canada.ca/src/data/covidLive/covid19.csv'  # noqa: E501
    INFO_PAGE = 'https://www.canada.ca/en/public-health/services/diseases/2019-novel-coronavirus-infection.html#a1'  # noqa: E501

    def __init__(self, path: PathLike, url: Optional[str] = None,
                 info: Optional[str] = None, update: bool = True):
        '''
        Parameters
        ----------
        path : path-like object
            the path (on disk) where the CSV file is located
        url : str, optional
            the URL to the Government of Canada's COVID-19 report; if not
            provided then it uses the default link
        info : str optional
            the URL to the main information path (not the CSV file); not
            provided then it uses the default link
        update : bool, optional
            if ``True`` then updates an existing CSV file to the latest version
        '''
        if url is None:
            url = PHACSource.CSV_URL

        if info is None:
            self._info = PHACSource.INFO_PAGE
        else:
            self._info = info

        path = pathlib.Path(path) / 'covid19.csv'
        if path.exists():
            if update:
                click.echo('Updating PHAC COVID-19 report.')
                _download(url, path)
        else:
            click.echo('Accessing PHAC COVID-19 report.')
            _download(url, path)

        self._path = path

    @classmethod
    def name(cls) -> str:
        return 'phac'

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
                    confirmed=int(entry['numtotal']),
                    resolved=-1,
                    deceased=int(entry['numdeaths'])
                )

    def testing(self) -> Generator[CaseTesting, None, None]:
        with self._path.open() as f:
            contents = csv.DictReader(f)
            for entry in contents:
                if entry['prname'] == 'Canada':
                    continue

                if len(entry['numtested']) == 0:
                    tested = 0
                else:
                    tested = int(entry['numtested'])

                yield CaseTesting(
                    date=_to_date(entry['date']),
                    province=entry['prname'],
                    country='Canada',
                    tested=tested,
                    under_investigation=-1
                )

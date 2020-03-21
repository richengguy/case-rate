from collections import OrderedDict
import csv
import functools
import pathlib
import subprocess
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse, urlunsplit

import click


def _git(*args, cwd: pathlib.Path = None,
         output_stdout: bool = False) -> Optional[str]:
    '''Run a git command using subprocess.

    This will just call the system's own 'git'.  For example, calling this with
    the arguments ``_git('clone', 'https://github.com/user/repo.git')`` is
    functionally the same as ``$ git clone https://github.com/user/repo.git``.

    Parameters
    ----------
    cwd : pathlib.Path
        the current working directory when running the 'git' command
    output_stdout : bool
        if ``True`` then return stdout instead of showing it
    '''
    cmd = ['git'] + list(args)
    output = subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)
    if output_stdout:
        return output.stdout
    else:
        click.echo(output.stdout)
        click.echo(output.stderr)


def _get_github_link(path: pathlib.Path = None) -> str:
    '''Get the link to the commit on GitHub.

    This is a link that can be visited by a browser and takes the form of
    ``https://github.com/<organization>/<repo>/tree/<commit-id>``.

    Parameters
    ----------
    path : pathlib.Path, optional
        path to the COVID-19 repo, by default None

    Returns
    -------
    str
        the URL to the commit on GitHub
    '''
    remote_url = urlparse(_git('config', '--get', 'remote.origin.url',
                               cwd=path, output_stdout=True))
    commit_id = _git('rev-parse', '--verify', 'HEAD',
                     cwd=path, output_stdout=True).decode()

    if b'github.com' not in remote_url.netloc:
        raise ValueError('Cannot get link for non-GitHub repos.')

    # Construct the GitHub path, which includes stripping out the '.git' that's
    # sometimes at the end of a git+http URL.
    github_path = pathlib.PurePosixPath(remote_url.path.decode())
    github_path = github_path.parent / github_path.stem / 'tree' / commit_id
    github_url = urlunsplit([remote_url.scheme, remote_url.netloc,
                             github_path.as_posix().encode(), '', ''])

    return github_url.decode().rstrip()


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


class Entry(object):
    '''A single entry within a daily report.

    Attributes
    ----------
    province: str or ``None``
        the sub-national region the entry is for; optional
    country: str
        the country the entry is for
    confirmed: int
        number of confirmed COVID-19 cases
    deaths: int
        number of COVID-19-related deaths
    recovered: int
        number of confirmed COVID-19 recoveries
    '''
    class _Fields(object):
        PROVINCE = 'Province/State'
        COUNTRY = 'Country/Region'
        CONFIRMED = 'Confirmed'
        DEATHS = 'Deaths'
        RECOVERED = 'Recovered'

    def __init__(self, row):
        def get(row: dict, field: str) -> Optional[str]:
            try:
                return row[field]
            except KeyError:
                return None

        def to_int(row: dict, field: str) -> int:
            value = get(row, field)
            if value is None:
                return 0

            try:
                return int(value)
            except ValueError:
                return 0

        self.province = get(row, Entry._Fields.PROVINCE)
        self.country = get(row, Entry._Fields.COUNTRY)
        self.confirmed = to_int(row, Entry._Fields.CONFIRMED)
        self.deaths = to_int(row, Entry._Fields.DEATHS)
        self.recovered = to_int(row, Entry._Fields.RECOVERED)


class Report(object):
    '''Represents the contents of a single "daily report" CSV file.

    Attributes
    ----------
    entries: list of ``Entry`` instances
        a list of all entries within the report
    '''
    def __init__(self,
                 path: Optional[pathlib.Path] = None,
                 entries: Optional[List[Entry]] = None):
        '''
        Parameters
        ----------
        path : pathlib.Path or ``None``
            path to the report CSV file
        entries: list of ``Entry`` objects, or ``None``
        '''
        if path is None and entries is None:
            raise ValueError('Need to provide either CSV path or entries.')
        if path is not None and entries is not None:
            raise ValueError('Can only have either path or entries, not both.')

        if path is not None:
            with path.open() as f:
                report = csv.DictReader(f)
                self._entries = [Entry(row) for row in report]
        elif entries is not None:
            self._entries = entries.copy()

    def __len__(self):
        return len(self._entries)

    @property
    def entries(self) -> List[Entry]:
        return self._entries

    @property
    def total_confirmed(self) -> int:
        '''Number of total confirmed cases in the report.'''
        return self.reduce(lambda confirmed, entry: confirmed + entry.confirmed)  # noqa: E501

    @property
    def total_deaths(self) -> int:
        '''Number of total deaths in the report.'''
        return self.reduce(lambda deaths, entry: deaths + entry.deaths)

    @property
    def total_recovered(self) -> int:
        '''Number of total recoveries in the report.'''
        return self.reduce(lambda recovered, entry: recovered + entry.recovered)  # noqa: E501

    def reduce(self, fn: Callable[[int, Entry], int]) -> int:
        '''Applies a reduction onto the report entries.'''
        return functools.reduce(fn, self._entries, 0)

    def for_country(self, country: str) -> 'Report':
        '''Obtain all reports for the particular country.

        Parameters
        ----------
        country : str
            the country name

        Returns
        -------
        Report
            another daily report with just the entries for that country
        '''
        return Report(
            entries=[
                entry for entry in self._entries if entry.country == country
            ]
        )


class ReportSet(object):
    '''A report of all COVID-19 cases in the dataset.

    This provides a simple mechanism to represent the contents of the
    repository.

    Attributes
    ----------
    dates: list of ``(year, month, day)``
        a list of all available dates within the report collection
    '''
    def __init__(self,
                 path: Optional[pathlib.Path] = None,
                 subset: Optional[OrderedDict] = None):
        '''
        Parameters
        ----------
        path : pathlib.Path
            path to the reports folder
        subset: collections.OrderedDict
            a subset of the reports, used to generate a new collection
        '''
        if path is None and subset is None:
            raise ValueError('Need to provide either CSV path or entries.')
        if path is not None and subset is not None:
            raise ValueError('Can only have either path or entries, not both.')

        if path is not None:
            files = path.glob('*.csv')

            reports = []
            for csvfile in files:
                date = _parse_name(csvfile)
                reports.append((date, Report(csvfile)))

            reports.sort(key=lambda entry: entry[0][2])  # sort by day
            reports.sort(key=lambda entry: entry[0][1])  # sort by month
            reports.sort(key=lambda entry: entry[0][0])  # sort by year

            self._reports = OrderedDict(reports)
        elif subset is not None:
            self._reports = subset

    def __len__(self):
        return len(self._reports)

    @property
    def dates(self) -> List[Tuple[int, int, int]]:
        return list(self._reports.keys())

    @property
    def reports(self) -> List[Report]:
        return list(self._reports.values())

    def for_country(self, country: str) -> 'ReportSet':
        '''Obtain the set of reports for just a single country.

        Parameters
        ----------
        country: str
            the name of the country

        Returns
        -------
        ReportSet
            a new report set with information on just that country
        '''
        subset: OrderedDict[Tuple[int, int, int], Report] = OrderedDict()
        for date, report in self._reports.items():
            entries = report.for_country(country)
            if len(entries) > 0:
                subset[date] = entries

        return ReportSet(subset=subset)


class Dataset(object):
    '''Represents the contents of a time-series dataset.

    Attributes
    ----------
    reports : ReportsCollection
        the collection of available daily reports
    github_link : str
        the browser-friendly link to the URL source
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
        path = pathlib.Path(path)
        if not path.exists():
            raise ValueError(f'{path} does not exist.')
        self._reports = ReportSet(path=path / Dataset.DAILY_REPORTS)
        self._link = _get_github_link(path)

    @property
    def github_link(self) -> str:
        return self._link

    @property
    def reports(self) -> ReportSet:
        return self._reports

    def for_country(self, country: str) -> ReportSet:
        '''Obtain the reports for a particular country.

        Parameters
        ----------
        country : str
            name of the country

        Returns
        -------
        ReportSet
            case data for just that country
        '''
        return self._reports.for_country(country)

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

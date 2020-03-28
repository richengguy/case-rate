from collections import OrderedDict
import csv
import functools
import pathlib
import subprocess
from typing import Callable, Dict, Iterator, List, Optional, Tuple
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
    '''
    def __init__(self, province: Optional[str], country: str, confirmed: str,
                 deaths: str):
        self.province = province
        self.country = country
        self.confirmed = int(confirmed)
        self.deaths = int(deaths)


class Report(object):
    '''Represents the contents of a single "daily report" CSV file.

    Attributes
    ----------
    entries: list of ``Entry`` instances
        a list of all entries within the report
    '''
    def __init__(self, entries: List[Entry]):
        '''
        Parameters
        ----------
        entries : list of ``Entry`` objects
            set of of report entries that make up the full report
        '''
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


_TimeSeries = Iterator[Tuple[Tuple[int], Report]]


def _validate_header(header: List[str]):
    '''Validate the header within the time series CSV file.

    This will throw an exception if the header is malformed (or has been
    changed).

    Parameters
    ----------
    header : List[str]
        list of header fields

    Raises
    ------
    RuntimeError
        if the header is invalid, with the reason being stored within the
        exception string
    '''
    expected_names = [
        'Province/State',
        'Country/Region',
        'Lat',
        'Long'
    ]
    for expected, found in zip(expected_names, header[0:5]):
        if expected != found:
            raise RuntimeError(
                f'Found {found} field in header; expected {expected}.')


def _parse_timeseries(csv_confirmed: pathlib.Path,
                      csv_deaths: pathlib.Path) -> _TimeSeries:
    '''Parses the time series CSVs into a set of daily reports.

    The parsing process will ensure that the reports are returned in
    chronological order.

    Parameters
    ----------
    csv_confirmed : pathlib.Path
        path to the CSV file with confirmed cases
    csv_deaths : pathlib.Path
        path to the CSV file with reported deaths

    Yields
    ------
    `(year, month, day)`
        a tuple with the date
    Report
        the day report object for that date
    '''
    with csv_confirmed.open() as f_conf, csv_deaths.open() as f_deaths:
        timeseries_confirmed = csv.reader(f_conf)
        timeseries_deaths = csv.reader(f_deaths)

        # Grab the headers and make sure that they match.
        header: List[str]
        header = next(timeseries_confirmed)
        _validate_header(header)

        if header != next(timeseries_deaths):
            raise RuntimeError('Time series headers do no match!')

        # Pull out all of the rows because they need to be transposed into
        # columns.
        rows_confirmed = [row for row in timeseries_confirmed]
        rows_deaths = [row for row in timeseries_deaths]

        if len(rows_confirmed) != len(rows_deaths):
            raise RuntimeError(
                'Number of rows in "confirmed" and "deaths" tables '
                'don\'t match.')

        if len(rows_confirmed[0]) != len(rows_deaths[0]):
            raise RuntimeError(
                'Number of columns in "confirmed" and "deaths" tables '
                'don\'t match.')

    num_cols = len(rows_confirmed[0])

    for column in range(4, num_cols):
        # Parse the date parameters.
        date = header[column].split('/')
        month, day, year = tuple(int(item) for item in date)
        year += 2000

        # Generate the daily report for each country/region.
        entries = []  # type: List[Entry]

        row_confirmed: List[str]
        row_deaths: List[str]
        for row_confirmed, row_deaths in zip(rows_confirmed, rows_deaths):
            country = row_confirmed[1]
            province = row_confirmed[0] if len(row_confirmed[0]) != 0 else None
            entries.append(
                Entry(province, country, row_confirmed[column],
                      row_deaths[column])
            )

        yield (year, month, day), Report(entries)


class ReportSet(object):
    '''A report of all COVID-19 cases in the dataset.

    This provides a simple mechanism to represent the contents of the
    repository.

    Attributes
    ----------
    dates: list of ``(year, month, day)``
        a list of all available dates within the report collection
    '''
    CONFIRMED_CASES = pathlib.Path('time_series_covid19_confirmed_global.csv')
    DEATHS = pathlib.Path('time_series_covid19_deaths_global.csv')

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
            confirmed = path / ReportSet.CONFIRMED_CASES
            deaths = path / ReportSet.DEATHS
            self._reports = OrderedDict()
            for date, report in _parse_timeseries(confirmed, deaths):
                self._reports[date] = report
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

    def filter(self, min_confirmed: Optional[int] = None,
               min_deaths: Optional[int] = None) -> 'ReportSet':
        '''Filter a report set based on some criteria.

        The filtering allows a new report set to be generated based on the
        number of confirmed cases or reported deaths.

        Parameters
        ----------
        min_confirmed : int, optional
            the minimum number of confirmed cases
        min_deaths : int
            the minimum number of reported deaths

        Returns
        -------
        ReportSet
            the filtered report set
        '''
        has_min_confirmed = min_confirmed is not None
        has_min_deaths = min_deaths is not None

        subset: OrderedDict[Tuple[int, int, int], Report] = OrderedDict()
        for date, report in self._reports.items():
            confirmed = report.total_confirmed
            deaths = report.total_deaths

            meets_min_confirmed = has_min_confirmed and confirmed >= min_confirmed  # noqa: E501
            meets_min_deaths = has_min_deaths and deaths >= min_deaths

            if meets_min_confirmed or meets_min_deaths:
                subset[date] = report

        return ReportSet(subset=subset)

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
    TIME_SERIES = DATA / pathlib.PurePath('csse_covid_19_time_series')

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
        self._reports = ReportSet(path=path / Dataset.TIME_SERIES)
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

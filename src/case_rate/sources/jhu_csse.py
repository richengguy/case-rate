import csv
import datetime
import pathlib
import subprocess
from typing import Generator, List, Optional, Tuple
from urllib.parse import urlparse, urlunsplit

import click

from case_rate._types import PathLike
from case_rate.storage import InputSource, Cases


def _git(*args, cwd: pathlib.Path = None) -> Tuple[str, str]:
    '''Run a git command using subprocess.

    This will just call the system's own 'git'.  For example, calling this with
    the arguments ``_git('clone', 'https://github.com/user/repo.git')`` is
    functionally the same as ``$ git clone https://github.com/user/repo.git``.

    Parameters
    ----------
    cwd : pathlib.Path
        the current working directory when running the 'git' command

    Returns
    -------
    stdout : str
        any output to standard out
    stderr : str
        any output to standard error
    '''
    cmd = ['git'] + list(args)
    output = subprocess.run(cmd, check=True, capture_output=True, cwd=cwd)
    return output.stdout, output.stderr


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
    query, _ = _git('config', '--get', 'remote.origin.url', cwd=path)
    remote_url = urlparse(query.strip())
    commit_id = _git('rev-parse', '--verify', 'HEAD', cwd=path)[0].decode()

    if b'github.com' not in remote_url.netloc:
        raise ValueError('Cannot get link for non-GitHub repos.')

    # Construct the GitHub path, which includes stripping out the '.git' that's
    # sometimes at the end of a git+http URL.
    github_path = pathlib.PurePosixPath(remote_url.path.decode())
    github_path = github_path.parent / github_path.stem / 'tree' / commit_id
    github_url = urlunsplit([remote_url.scheme, remote_url.netloc,
                             github_path.as_posix().encode(), '', ''])

    return github_url.decode().rstrip()


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


def _parse_csv(path: pathlib.Path) -> Tuple[List[str], List[List[str]]]:
    '''Parses the CSV file at the specified location.

    Parameters
    ----------
    path : path object
        path to a CSV file

    Returns
    -------
    header : list of ``str``
        the CSV file's header
    contents : list of lists
        a list of string lists with the CSV's data
    '''
    with path.open() as f:
        contents = csv.reader(f)

        # Verify the header is correct.
        header = next(contents)
        _validate_header(header)

        # Get the CSV contents.
        rows = [row for row in contents]

    return header, rows


class JHUCSSESource(InputSource):
    '''Use John Hopkins University's COVID-19 as an input data source.

    JHU's Center for Systems Science and Engineering provides a COVID-19 report
    up on GitHub (https://github.com/CSSEGISandData/COVID-19).  This input
    source pulls the latest version of the repo and provides an interface to
    the time series data.
    '''
    DEFAULT_REPO = 'https://github.com/CSSEGISandData/COVID-19'

    def __init__(self, path: PathLike, repo: Optional[str] = None):
        '''
        Parameters
        ----------
        path : path-like
            path to where the repo will be locally stored
        repo : str, optional
            URL to COVID-19 report, will default to the GitHub repository
        '''
        if repo is None:
            repo = JHUCSSESource.DEFAULT_REPO

        path = pathlib.Path(path)
        if not path.exists():
            click.echo(f'Cloning "{repo}" to "{path}".')
            stdout, stderr = _git('clone', repo, path.as_posix())
        else:
            click.echo(f'Updating JHU-CSSE COVID-19 dataset at "{path}".')
            stdout, stderr = _git('pull', cwd=path)

        click.secho('stdout', fg='green', bold=True)
        click.echo(stdout)
        if len(stderr) != 0:
            click.secho('stderr', fg='red', bold=True)
            click.echo(stderr)

        self._path = path
        self._url = _get_github_link(path)

    @property
    def name(self):
        return "jhu-csse"

    @property
    def details(self):
        return "JHU-CSSE COVID-19 Report"

    @property
    def url(self):
        return self._url

    def cases(self) -> Generator[Cases, None, None]:
        csse_covid_19_time_series = self._path / 'csse_covid_19_data' / 'csse_covid_19_time_series'  # noqa: E501

        # Get paths to the various CSV files.
        csv_confirmed = csse_covid_19_time_series / 'time_series_covid19_confirmed_global.csv'  # noqa: E501
        csv_deceased = csse_covid_19_time_series / 'time_series_covid19_deaths_global.csv'  # noqa: E501

        # Parse the files.
        header, rows_confirmed = _parse_csv(csv_confirmed)
        header_deceased, rows_deceased = _parse_csv(csv_deceased)

        # Check the data consistency.
        numel_confirmed = sum(len(row) for row in rows_confirmed)
        numel_deceased = sum(len(row) for row in rows_deceased)

        if header != header_deceased:
            raise RuntimeError('Confirmed and deceased headers don\'t match.')

        same_size = numel_confirmed == numel_deceased
        if not same_size:
            raise RuntimeError(
                f'CSV content sizes are different '
                f'(confirmed: {numel_confirmed}, deceased: {numel_deceased}).'
            )

        # Extract the data.
        for column in range(4, len(header)):
            month, day, year = tuple(int(dd) for dd in header[column].split('/'))  # noqa: E501
            date = datetime.date(year+2000, month, day)
            for confirmed, deceased in zip(rows_confirmed, rows_deceased):
                yield Cases(
                    date=date,
                    province=confirmed[0],
                    country=confirmed[1],
                    confirmed=confirmed[column],
                    resolved=-1,
                    deceased=deceased[column]
                )

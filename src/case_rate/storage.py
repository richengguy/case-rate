import abc
import datetime
import sqlite3
from typing import Any, Generator, NamedTuple, Optional

from ._types import PathLike

__all__ = [
    'Storage'
]


# Ensure dates are stored correctly within the database.
def _adapt_date(date: datetime.date) -> str:
    return f'{date.year}-{date.month}-{date.day}'


def _convert_date(value: bytes) -> Any:
    parts = value.split('-')
    year, month, day = tuple(int(part) for part in parts)
    return datetime.date(year, month, day)


sqlite3.register_adapter(datetime.date, _adapt_date)
sqlite3.register_converter('timestamp', _convert_date)


class Cases(NamedTuple):
    date: datetime.date
    province: str
    country: str
    confirmed: int
    deceased: int
    resolved: int


class Testing(NamedTuple):
    date: datetime.date
    province: str
    country: str
    tested: int
    under_investigation: int


class InputSource(abc.ABC):
    '''Defines an object that case provide data to the storage backend.

    Attributes
    ----------
    name : str
        a unique identifier for the input source
    details : str
        a more friendly description when displaying the source information
    url : str
        a URL to the source location
    '''
    @abc.abstractproperty
    def name(self) -> str:
        pass

    @abc.abstractproperty
    def details(self) -> str:
        pass

    @abc.abstractproperty
    def url(self) -> str:
        pass

    @abc.abstractmethod
    def cases(self) -> Generator[Cases, None, None]:
        '''The number of COVID-19 cases and their current status.

        Yields
        ------
        :class:`Cases`
            A named tuple containing the date and the number of confirmed,
            resolved and deceased cases.
        '''

    @abc.abstractmethod
    def testing(self) -> Generator[Testing, None, None]:
        '''The number of COVID-19 tests (completed and in-progress).

        Yields
        ------
        :class:`Testing`
            A named tuple containing the date and the number of completed and
            in-progress tests.
        '''


class Storage:
    '''Creates the storage backend used by the covid19 application.

    The storage backend is a simple in-memory SQLite database.  It's designed
    to support ingesting information from multiple sources and putting them
    into a single, uniform database.
    '''
    class Error(Exception):
        '''Used to indicate that something went wrong with the backend.'''

    class _Source(NamedTuple):
        name: str
        details: str
        url: str
        source_id: int

    def __init__(self, path: PathLike = ':memory:'):
        '''
        Parameters
        ----------
        path : path-like object, optional
            path to where the SQLite data is stored, by default ':memory:'
        '''
        detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        self._conn = sqlite3.connect(path, detect_types=detect_types)
        self._conn.row_factory = sqlite3.Row

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, type, value, traceback):
        self._conn.close()

    def initialize(self):
        '''Initialize the internal SQL tables.

        This will create any of the necessary tables if they don't already
        exist in the database.  Tables are created with the ``IF NOT EXISTS``
        option so calling this is safe, even on an existing database.

        Raises
        ------
        :exc:`StorageError`
            if something went wrong when initializing the backend
        '''
        try:
            with self._conn:
                self._conn.executescript('''
                CREATE TABLE IF NOT EXISTS sources (
                    name TEXT,
                    details TEXT,
                    url TEXT,
                    UNIQUE (name)
                );
                CREATE TABLE IF NOT EXISTS cases (
                    date DATE,
                    province TEXT
                    country TEXT,
                    confirmed INTEGER,
                    recovered INTEGER,
                    deceased INTEGER,
                    source INTEGER,
                    FOREIGN KEY (source) REFERENCES sources(name)
                );
                CREATE TABLE IF NOT EXISTS testing (
                    date DATE,
                    province TEXT,
                    country TEXT,
                    tested INTEGER,
                    under_investigation INTEGER,
                    source INTEGER,
                    FOREIGN KEY (source) REFERENCES sources(name)
                )
                ''')
        except sqlite3.IntegrityError as e:
            raise Storage.Error('Failed to initialize storage backend.') from e

    def populate(self, source: InputSource):
        '''Populate the database with the contents from an input source.

        Parameters
        ----------
        source : :class:`InputSource`
            an input source object that will populate the internal database
        '''
        with self._conn:
            # Check if the source exists and if not, register it.
            pass

    def _get_source(self, source: InputSource) -> Optional['Storage._Source']:
        '''Obtain the database reference for the current source.

        Parameters
        ----------
        source : :class:`InputSource`
            an input source object

        Returns
        -------
        _Source or ``None``
            the input source; will be ``None`` if it's not in the database
        '''
        with self._conn:
            cursor = self._conn.cursor()
            row = cursor.execute(
                'SELECT rowid, * FROM sources WHERE name == ?',
                (source.name,)).fetchone()
            if row is None:
                return None

            return Storage._Source(row['name'], row['details'], row['url'],
                                   row['rowid'])

    def _register(self, source: InputSource) -> 'Storage._Source':
        '''Register the input source with the database.

        Parameters
        ----------
        source : InputSource
            the input source being registered

        Returns
        -------
        _Source
            a database reference to the input source
        '''
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(
                'INSERT INTO sources (name, details, url) VALUES (?,?,?)',
                (source.name, source.details, source.url))

        ref = self._get_source(source)
        if ref is None:
            raise Storage.Error('Failed to register source with the backend.')

        return ref

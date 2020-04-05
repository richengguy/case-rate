import abc
import datetime
import sqlite3
from typing import (Any, Dict, Generator, List, NamedTuple, Optional, Tuple,
                    Union)

from ._types import PathLike

__all__ = [
    'InputSource',
    'Storage'
]


def _generate_select(table: str, fields: Tuple[str],
                     region: Tuple[Optional[str]] = (None, None)
                     ) -> Tuple[str, Tuple[str]]:
    '''Generates a select statement for SQL queries.

    Parameters
    ----------
    table : str
        name of the table to query
    fields : Tuple[str]
        list of columns to retrieve
    region : ``(province, country)``, optional
        region to select, by default ``(None, None)``

    Returns
    -------
    statement : str
        the SQL 'select' statement
    region : ``(province, country)``
        the region tuple, but filtered so that it can be passed along correctly
        the select statement
    '''
    filtered = []
    province, country = region

    columns = ', '.join(fields)
    query = f'SELECT {columns} FROM {table} WHERE source == ?'

    if province is not None:
        query += ' AND province == ?'
        filtered.append(province)

    if country is not None:
        query += ' AND country == ?'
        filtered.append(country)

    return query, tuple(filtered)


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


class CaseTesting(NamedTuple):
    date: datetime.date
    province: str
    country: str
    tested: int
    under_investigation: int


class InputSource(abc.ABC):
    '''Defines an object that case provide data to the storage backend.

    A subclass must define the attribute.  It can also implement :meth:`cases`
    or :meth:`testing` depending on what information the report presents.  The
    default implementations do nothing.

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

    def cases(self) -> Generator[Cases, None, None]:
        '''The number of COVID-19 cases and their current status.

        Yields
        ------
        :class:`Cases`
            A named tuple containing the date and the number of confirmed,
            resolved and deceased cases.
        '''
        return []

    def testing(self) -> Generator[CaseTesting, None, None]:
        '''The number of COVID-19 tests (completed and in-progress).

        Yields
        ------
        :class:`CaseTesting`
            A named tuple containing the date and the number of completed and
            in-progress tests.
        '''
        return []


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

    @property
    def sources(self) -> Dict[str, Tuple[str, str]]:
        rows = self._conn.execute('SELECT * FROM sources')

        sources: Dict[str, Tuple[str, str]] = {}
        for row in rows:
            sources[row['name']] = (row['details'], row['url'])

        return sources

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
                    province TEXT,
                    country TEXT,
                    confirmed INTEGER,
                    resolved INTEGER,
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
            cursor = self._conn.cursor()

            # Check if the source exists and if not, register it.
            ref = self._get_source(source.name)
            if ref is None:
                ref = self._register(source)

            # Populate the set of confirmed cases.
            cases: Cases
            for cases in source.cases():
                cursor.execute(
                    'INSERT INTO cases VALUES (?,?,?,?,?,?,?)',
                    (cases.date, cases.province, cases.country,
                     cases.confirmed, cases.resolved, cases.deceased,
                     ref.source_id))

            # Populate the testing data.
            tests: CaseTesting
            for tests in source.testing():
                cursor.execute(
                    'INSERT INTO testing VALUES (?,?,?,?,?,?)',
                    (tests.date, tests.province, tests.country,
                     tests.tested, tests.under_investigation,
                     ref.source_id)
                )

    def all_cases(self, source: Union[str, InputSource]) -> List[Cases]:
        '''Return a list of all cases for the input source.

        Parameters
        ----------
        source : a string or :class:`InputSource`
            the input source to retrieve

        Returns
        -------
        list of :class:`Cases`
            All available cases in the database for the input source.
        '''

        cases: List[Cases] = []
        for row in self._select(source, 'cases', Cases._fields):
            cases.append(Cases(**row))

        return cases

    def all_tests(self, source: Union[str, InputSource]) -> List[CaseTesting]:
        '''Return a list of all testing statuses for the input source.

        Parameters
        ----------
        source : a string or :class:`InputSource`
            the input source to retrieve

        Returns
        -------
        list of :class;`CaseTesting`
            All available testing results for the input source.
        '''
        tests: List[CaseTesting] = []
        for row in self._select(source, 'testing', CaseTesting._fields):
            tests.append(CaseTesting(**row))

        return tests

    def _select(self,
                source: Union[str, InputSource],
                table: str,
                fields: Tuple[str],
                region: Tuple[Optional[str]] = (None, None)
                ) -> Generator[Dict[str, Any], None, None]:
        '''Pull rows from the database.

        Parameters
        ----------
        source : ``str`` or :class:`InputSource`
            the input source to retrieve
        table : str
            the table being accessed
        fields : tuple of ``str``
            columns to retrieve
        region : ``(province, country)``
            the nation or subnational region to retrieve; if both are provided
            then it's treated as an "and" condition

        Yields
        ------
        list of dictionaries
            the obtained rows
        '''
        ref = self._get_source(source)
        query, region = _generate_select(table, fields, region)
        rows = self._conn.execute(query, (ref.source_id, *region))

        for row in rows:
            yield row

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
        name = source.name if isinstance(source, InputSource) else source
        with self._conn:
            cursor = self._conn.cursor()
            row = cursor.execute(
                'SELECT rowid, * FROM sources WHERE name == ?',
                (name,)).fetchone()

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

        ref = self._get_source(source.name)
        if ref is None:
            raise Storage.Error('Failed to register source with the backend.')

        return ref

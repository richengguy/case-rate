import abc
import datetime
import sqlite3
from typing import Any

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


class StorageError(Exception):
    '''Used to indicate that something went wrong with the storage backend.'''


class InputSource(abc.ABC):
    '''Defines an object that case provide data to the storage backend.'''


class Storage:
    '''Creates the storage backend used by the covid19 application.

    The storage backend is a simple in-memory SQLite database.  It's designed
    to support ingesting information from multiple sources and putting them
    into a single, uniform database.
    '''
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
                    under_investigation INTEGER
                )
                ''')
        except sqlite3.IntegrityError as e:
            raise StorageError('Failed to initialize storage backend.') from e

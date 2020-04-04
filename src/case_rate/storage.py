import abc
import pathlib
import sqlite3
from typing import Union

__all__ = [
    'Storage'
]


PathLike = Union[str, pathlib.Path]


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

import pathlib
from typing import Optional

from .jhu_csse import JHUCSSESource
from .phac import PHACSource
from .public_health_ontario import PublicHealthOntarioSource

from ..storage import InputSource

__all__ = [
    'DATA_SOURCES',
    'init_source',
    'select_source'
]


DATA_SOURCES = {
    (None, None): JHUCSSESource,    # Default source
    ('Canada', None): PHACSource,   # Canada-specific source
    ('Canada', 'Ontario'): PublicHealthOntarioSource  # Ontario-specific Source
}


def select_source(region: Optional[str] = None,
                  sources=DATA_SOURCES) -> InputSource:
    '''Select a data source to use for COVID-19 data.

    The source selector uses a simple string format to obtain the input data
    source.  The syntax is:

    * ``country`` to select a data source for a particular country or nation
      state
    * ``country:province`` to select a data source for a particular province
      (or state, region, voivodeship, etc.)

    The resolution order is to check an see if the specific
    ``country:province`` exists.  If not, it will then check for a nation-level
    data source.  Finally, it will pick the default source if nothing else is
    available.

    For example, ``Canada:Ontario`` will select a data source just for the
    Province of Ontario while ``Canada`` will select a more general Canadian
    data source.  However, if the an Ontario-only data source doesn't exist, it
    will default to the ``Canada`` source.

    Parameters
    ----------
    region : str, optional
        a region string of the form ``country:province``
    source : dict, optional
        a dictionary containing the sources to query; a default set is provided
        but can be modified if necessary

    Returns
    -------
    InputSource
        the requested input source or the default if the requested one is not
        available
    '''
    default = (None, None)
    if region is None:
        return sources[default]

    parts = region.split(':')
    if len(parts) == 1:
        key = (parts[0], None)
    elif len(parts) == 2:
        key = (parts[0], parts[1])
    else:
        raise NotImplementedError(
            'Subprovince (e.g. county-level) selection not implemented.')

    # Specific key matched.
    if key in sources:
        return sources[key]

    # General key matched.
    key = (key[0], None)
    if key in sources:
        return sources[key]

    # No matches; return default.
    return sources[default]


def init_source(path, update, region: Optional[str] = None, params: dict = {},
                sources=DATA_SOURCES) -> InputSource:
    '''Initialize a new :class:`InputSource` object.

    This will select the input source and then create a new instance of it.
    The ``path`` and ``update`` arguments are used to indicate the input
    sources working directory and whether or not it should attempt to update
    itself.  The function takes care of creating the appropriate working
    directory before the initialization happens.

    An optional dictionary, ``params`` can be used to set any extra input
    arguments for the input sources.  The dictionary key must be the input
    source name.

    Parameters
    ----------
    path : path-like object
        working directory used to store the input source's data
    update : bool
        if ``True`` then the data source should also try to update itself
    region : str, optional
        a region string of the form ``country:province``, by default None
    params : dict, optional
        dictionary with any extra parameters that are needed by the input
        sources, by default {}
    sources : dict, optional
        a dictionary containing the sources to query; a default set is provided
        but can be modified if necessary

    Returns
    -------
    :class:`InputSource`
        the initialized input source
    '''
    SourceCls = select_source(region, sources)

    working_path: pathlib.Path = pathlib.Path(path) / SourceCls.name()
    if not working_path.exists():
        working_path.mkdir(parents=True, exist_ok=False)

    try:
        options = params[SourceCls.name()]
    except KeyError:
        options = {}

    return SourceCls(path=working_path, update=update, **options)

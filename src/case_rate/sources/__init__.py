from typing import Optional

from .jhu_csse import JHUCSSESource
from .phac import PHACSource

from ..storage import InputSource

DATA_SOURCES = {
    (None, None): JHUCSSESource,    # Default source
    ('Canada', None): PHACSource    # Canada-specific source
}


def get_source(region: Optional[str] = None,
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

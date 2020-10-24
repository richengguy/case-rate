from typing import Optional, Tuple


def _parse_region_selector(region: Optional[str]) -> Tuple[Optional[str], Optional[str]]:  # noqa: E501
    '''Parses the region selection format.'''
    if region is None:
        return (None, None)

    parts = region.split(':')
    if len(parts) == 1:
        return (parts[0], None)
    elif len(parts) == 2:
        return (parts[0], parts[1])
    else:
        raise ValueError('Expected "<country>:<province/state>" selector.')

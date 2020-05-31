from typing import Optional, Tuple

import click


def parse_region_selector(region: Optional[str]) -> Tuple[Optional[str], Optional[str]]:  # noqa: E501
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


def echo_item(title: str, item: str):
    '''Echos a string of the form "**<title>:** <item>".

    Parameters
    ----------
    title : str
        a tile (will be bolded)
    item : str
        the string to display
    '''
    title = click.style(f'{title}:', bold=True)
    click.echo(f'{title} {item}')

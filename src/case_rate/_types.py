import datetime
import pathlib
from typing import NamedTuple, Union

__all__ = [
    'Cases',
    'CaseTesting',
    'PathLike'
]

PathLike = Union[str, pathlib.Path]
Datum = Union['Cases', 'CaseTesting']


class Cases(NamedTuple):
    '''Report the number of cases at some date.

    Attributes
    ----------
    date : :class:`datetime.date`
        date when cases where reported
    province : string
        the subnational region (e.g., province, state, etc.) that the cases are
        reported for
    country : string
        the national region (e.g., national state, autonomous region, etc.)
        that the cases are reported for
    confirmed : int
        number of confirmed cases
    deceased : int
        number of deaths confirmed due to COVID-19
    resolved : int
        number of confirmed resolved cases
    '''
    date: datetime.date
    province: str
    country: str
    confirmed: int
    deceased: int
    resolved: int

    def __add__(self, other: 'Cases') -> 'Cases':  # type: ignore
        if not isinstance(other, self.__class__):
            raise TypeError('Must only add to another Cases object.')

        if self.date != other.date:
            raise ValueError('Cannot add case status for different dates.')

        province = self.province if other.province == self.province else 'aggr'
        country = self.country if other.country == self.country else 'aggr'

        # Only add resolved cases if both are positive.  A negative value means
        # no information is available.
        if self.resolved >= 0 and other.resolved >= 0:
            resolved = self.resolved + other.resolved
        else:
            resolved = self.resolved

        return Cases(
            date=self.date,
            province=province,
            country=country,
            confirmed=self.confirmed + other.confirmed,
            deceased=self.deceased + other.deceased,
            resolved=resolved
        )


class CaseTesting(NamedTuple):
    '''Report the current testing level at some date.

    Attributes
    ----------
    date : :class:`datetime.date`
        date when cases where reported
    province : string
        the subnational region (e.g., province, state, etc.) that the cases are
        reported for
    country : string
        the national region (e.g., national state, autonomous region, etc.)
        that the cases are reported for
    tested : int
        total number of individuals tested for COVID-19
    under_investigation : int
        number of individuals still under investigation for COVID-19 (i.e.,
        incomplete tests)
    '''
    date: datetime.date
    province: str
    country: str
    tested: int
    under_investigation: int

    def __add__(self, other: 'CaseTesting') -> 'CaseTesting':  # type: ignore
        if not isinstance(other, self.__class__):
            raise TypeError('Must only add to another CaseTesting object.')

        if self.date != other.date:
            raise ValueError('Cannot add testing status for different dates.')

        province = self.province if other.province == self.province else 'aggr'
        country = self.country if other.country == self.country else 'aggr'
        return CaseTesting(
            date=self.date,
            province=province,
            country=country,
            tested=self.tested + other.tested,
            under_investigation=(self.under_investigation +
                                 other.under_investigation)
        )


class SourceInfo(NamedTuple):
    '''Used to specify information about where the data came from.'''
    description: str
    url: str

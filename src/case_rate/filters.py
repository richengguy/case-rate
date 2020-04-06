import datetime
from case_rate.storage import Cases, CaseTesting
from typing import Callable, Dict, List, Union

_Info = Union[Cases, CaseTesting]
_InfoList = Union[List[Cases], List[CaseTesting]]


def select(cases: _InfoList, fn: Callable[[_Info], bool]) -> _InfoList:
    '''Filters the list of cases based on some criteria.

    Parameters
    ----------
    cases : list of either :class:`Cases` or :class:`CaseTesting`
        list of cases to filter
    fn : callable ``(Cases) -> bool`` or ``(CaseTesting) -> bool``
        a functor that can be used to filter the selected cases

    Returns
    -------
    list of :class:`Cases` or :class:`CaseTesting`
        filtered list, with the items sorted by date
    '''
    filtered = filter(fn, cases)
    return sorted(filtered, key=lambda item: item.date)


def select_by_country(cases: _InfoList, country: str) -> _InfoList:
    '''Filter the list of cases by country.

    Parameters
    ----------
    cases : list of :class:`Cases`
        list of cases to filter
    country : str
        country to select

    Returns
    -------
    list of :class:`Cases`
        list filtered by country
    '''
    return select(cases, lambda case: case.country == country)


def sum_by_date(cases: _InfoList) -> _InfoList:
    '''Sum cases or testing status by date.

    Parameters
    ----------
    cases : list of either :class:`Cases` or :class:`CaseTesting`
        list of cases to sum

    Returns
    -------
    list of :class:`Cases`
        list of cases, but where each element is summed by date; if there are
        multiple countries/provinces then that information is lost
    '''
    summed: Dict[datetime.date, _Info] = {}
    for case in cases:
        if case.date in summed:
            summed[case.date] += case
        else:
            summed[case.date] = case

    dates: List[datetime.date] = sorted(summed.keys())
    return list(summed[date] for date in dates)

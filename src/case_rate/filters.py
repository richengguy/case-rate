import datetime
from case_rate.storage import Cases, CaseTesting
from typing import Dict, List, Union

_Info = Union[Cases, CaseTesting]
_InfoList = Union[List[Cases], List[CaseTesting]]


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
    def select(case: _Info) -> bool:
        return case.country == country

    filtered = filter(select, cases)
    return list(filtered)


def sum_by_date(cases: _InfoList) -> _InfoList:
    '''Sum cases or testing status by date.

    Parameters
    ----------
    cases : list of either :class:`Cases` of :class:`CaseTesting`
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

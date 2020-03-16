import datetime
from typing import List, Tuple

import numpy as np

from case_rate.dataset import DailyReport, Report


class TimeSeries(object):
    '''Processes a report data set into a time series.

    Attributes
    ----------
    dates: list of ``datetime.date`` objects
        the dates for each element in the time series
    days: list of ``int``
        a list where each element indicates the number of days since start
        (first element is always zero)
    confirmed: list of ``int``
        number of confirmed COVID-19 cases
    deaths: list of ``int``
        number of COVID-19-related deaths
    recovered: list of ``int``
        number of confirmed COVID-19 recoveries
    '''
    def __init__(self, report: Report):
        '''
        Parameters
        ----------
        dataset : Dataset
            the data set the time seris is for.
        '''
        daily: DailyReport
        self.dates = [datetime.date(year, month, day) for year, month, day in report.dates]  # noqa: E501
        self.days = [(self.dates[0] - date) for date in self.dates]
        self.confirmed = [daily.total_confirmed for daily in report.reports]
        self.deaths = [daily.total_deaths for daily in report.reports]
        self.recovered = [daily.total_recovered for daily in report.reports]

    def as_list(self) -> List[Tuple[int, int, int]]:
        '''Convert the time series into a list.'''
        return list(zip(self.confirmed, self.deaths, self.recovered))

    def as_numpy(self) -> np.ndarray:
        '''Convert the time series into a numpy array.'''
        return np.array(self.as_list())

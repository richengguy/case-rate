import datetime
from typing import List, Tuple

import numpy as np
import scipy.signal

from case_rate.dataset import Report, ReportSet


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
    def __init__(self, reports: ReportSet):
        '''
        Parameters
        ----------
        reports: ReportSet
            the report set to represent as a time series
        '''
        daily: Report
        self.dates = [datetime.date(year, month, day) for year, month, day in reports.dates]  # noqa: E501
        self.days = [(date - self.dates[0]).days for date in self.dates]
        self.confirmed = [daily.total_confirmed for daily in reports.reports]
        self.deaths = [daily.total_deaths for daily in reports.reports]
        self.recovered = [daily.total_recovered for daily in reports.reports]

    def as_list(self) -> List[Tuple[int, int, int]]:
        '''Convert the time series into a list.'''
        return list(zip(self.confirmed, self.deaths, self.recovered))

    def as_numpy(self) -> np.ndarray:
        '''Convert the time series into a numpy array.'''
        return np.array(self.as_list(), dtype=float)

    @staticmethod
    def crosscorrelate(s1: 'TimeSeries', s2: 'TimeSeries') -> np.ndarray:
        '''Compute the cross-correlation between two time series.

        The correlation is done in the log-domain.  This will perform some
        pre-processing to ensure that different length sequences are handled
        correctly.  It will also add a small `epsilon` for any zero-valued
        entry, which will appear as a value, after a log-transform, of -6.

        Parameters
        ----------
        s1 : TimeSeries
            first time series
        s2 : TimeSeries
            second time series

        Returns
        -------
        np.ndarray
            a Nx4 array containing the cross-correlation between the two time
            series
        '''
        x1 = s1.as_numpy()
        x2 = s2.as_numpy()
        N = max(x1.shape[0], x2.shape[0])
        num_measures = x1.shape[1]

        # Set zero entries to 1e-6 so a log-transform is possible.
        x1[x1 < 1] = 1e-6
        x2[x2 < 1] = 1e-6

        # Apply a log-10 transform.
        x1 = np.log10(x1)
        x2 = np.log10(x2)

        xcorr: List[np.ndarray] = []
        for i in range(num_measures):
            u = (x1[:, i] - np.mean(x1[:, i])) / np.std(x1[:, i])
            v = (x2[:, i] - np.mean(x2[:, i])) / np.std(x2[:, i])
            xcorr.append(scipy.signal.correlate(u, v) / N)

        max_lag = xcorr[0].shape[0] // 2
        lags = np.arange(-max_lag, max_lag+1)
        xcorr = np.vstack((lags, *xcorr)).transpose()
        return xcorr

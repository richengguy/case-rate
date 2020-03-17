import datetime
from typing import List, Tuple, Union

import numpy as np
import scipy.signal
import scipy.stats

from case_rate.dataset import Report, ReportSet


class _LeastSq(object):
    '''Object returned by the :meth:`_local_leastsq` function.'''
    def __init__(self, num_samples: int):
        self.slope = np.zeros((num_samples, 1))
        self.intercept = np.zeros((num_samples, 1))
        self.confidence_slope = np.zeros((num_samples, 1))
        self.confidence_intercept = np.zeros((num_samples, 1))
        self.smooth = np.zeros((num_samples, 1))

    def package(self) -> np.ndarray:
        lower = self.slope - self.confidence_slope
        upper = self.slope + self.confidence_slope
        return np.hstack((self.slope, lower, upper))


def _local_leastsq(x: np.ndarray, t: np.ndarray, k: int = 7,
                   alpha: float = 0.9) -> _LeastSq:
    '''Computes the local least-squares on the input time sequence.

    This assumes that the input sequence is locally linear (defaults to +/-3
    samples before and after current one).  It attempts to fit a line at each
    point given a local window.

    Parameters
    ----------
    data : list of ``int``
        sample values
    time : list of ``int``
        time indices
    k : int
        size of the sliding window
    alpha : float
        requested confidence interval

    Returns
    -------
    np.ndarray
        a Nx4 array, with the first two columns being the slope and intercept
        and the other two being their confidence intervals
    '''
    if k < 5:
        raise ValueError('Window size cannot be smaller than "5".')

    if x.shape[0] != t.shape[0]:
        raise ValueError('Samples and time indices must be same length.')

    num_samples = x.shape[0]
    result = _LeastSq(num_samples)

    for i in range(num_samples):
        i_min = max(0, i - k // 2)
        i_max = min(num_samples - 1, i + k // 2) + 1
        n = i_max - i_min

        # Compute least square values.
        x_sum = x[i_min:i_max].sum()
        t_sum = t[i_min:i_max].sum()
        t2_sum = (t[i_min:i_max]**2).sum()
        xt_sum = (x[i_min:i_max]*t[i_min:i_max]).sum()

        # Compute covariances.
        Sxx = t2_sum - (t_sum**2) / n
        Sxy = xt_sum - x_sum*t_sum / n

        # Compute parameters.
        slope = Sxy / Sxx
        intercept = x_sum / n - slope * t_sum / n

        result.slope[i] = slope
        result.intercept[i] = intercept

        # Compute confidence intervals.
        x_est = slope*t[i_min:i_max] + intercept
        mse = np.sum((x[i_min:i_max] - x_est)**2) / (n - 2)

        stderr_slope = np.sqrt(mse / Sxx)
        stderr_intercept = np.sqrt(mse / n)

        students_t = scipy.stats.t.ppf(alpha, n - 1)

        result.confidence_slope[i] = students_t*stderr_slope
        result.confidence_intercept[i] = students_t*stderr_intercept

        # Compute the "smooth" curve value.
        result.smooth[i] = slope*t[i] + intercept

    return result


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

    def growth_factor(self, return_filtered: bool = False) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:  # noqa: E501
        '''Computes the time series growth factor.

        The growth value is defined as the ratio between successive samples of
        the time series first derivative.  E.g.,

        ..math::

            G[i] = \\frac{\\Delta_i}{\\Delta_{i-1}}

        It is calculated by using a local least-squares approximation to
        compute the time series first derivative.  The forward difference is
        then taken in the log-domain to compute :math:`G[i]`.

        Parameters
        ----------
        return_filtered : bool
            if set to ``True`` then return the filtered curve

        Returns
        -------
        growth : np.ndarray
            a Nx3 array containing the estimated multiplication rate along with
            the confidence intervals
        filtered : np.ndarray
            the filtered time series, produced when estimating the derivatives
        '''
        confirmed = np.array(self.confirmed)
        time = np.array(self.days, dtype=float)
        filtered = _local_leastsq(confirmed, time)
        filtered_derivatives = filtered.package()

        # Handle derivatives close to zero.
        invalid = np.isclose(filtered_derivatives, 0)
        valid = np.logical_not(invalid)

        log_derivatives = np.zeros_like(filtered_derivatives)
        log_derivatives[invalid] = np.nan
        log_derivatives[valid] = np.log10(filtered_derivatives[valid])

        # Compute the growth factor in the log-domain (better numerical
        # properties).
        gf = np.zeros_like(filtered_derivatives)
        for i in range(len(self.confirmed)):
            if i == 0:
                continue
            if invalid[i].any() or invalid[i-1].any():
                gf[i, :] = np.nan

            delta = log_derivatives[i, :] - log_derivatives[i-1, :]
            gf[i, :] = np.power(10, delta)

        if return_filtered:
            return gf, filtered.smooth
        else:
            return gf

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

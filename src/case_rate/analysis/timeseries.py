import datetime
from typing import List, Union

import numpy as np

from .least_squares import LeastSquares, evalpoly, derivative
from .. import filters
from .._types import Cases, CaseTesting

Datum = Union[Cases, CaseTesting]


class TimeSeries:
    '''Represent some time series data and apply some processing to it.

    Attributes
    ----------
    dates : list of :class:`datetime.date` instances
        list of dates the time series represents
    daily_change : np.ndarray
        a convenience accessor to obtain the day-to-day changes via a finite
        difference
    '''
    def __init__(self, data: List[Datum], field: str, min_value: int = 0):
        '''
        Parameters
        ----------
        data : list of :class:`Cases` or :class:`CaseTesting`
            a list of either :class:`Cases` or :class:`CaseTesting` objects
        field : str
            the name of the field to use for the time series
        min_value : int
            don't include any data below this threshold
        '''
        def filter_by_field(datum: Datum) -> bool:
            return datum._asdict()[field] >= min_value

        data = filters.select(data, filter_by_field)
        data = filters.sum_by_date(data)

        start_date = data[0].date
        end_date = data[-1].date

        # Convert the case/testing data into a time series.
        duration = (end_date - start_date).days + 1
        dates = [start_date + datetime.timedelta(days=i) for i in range(duration)]  # noqa: E501
        samples = np.zeros((duration,))

        datum: Datum
        for i, datum in enumerate(data):
            value = datum._asdict()[field]
            if value < min_value:
                continue

            # The computed index and enumerated index should be the same.  If
            # not, then some duplicate data wasn't reported.  Fill it in using
            # nearest-neighbour interpolation (not actually interpolation).
            index = (datum.date - data[0].date).days
            if index > i:
                last_index = (data[i-1].date - data[0].date).days
                for j in range(last_index, index):
                    samples[j] = samples[last_index]

            samples[index] = datum._asdict()[field]

        self._start = start_date
        self._dates = dates
        self._samples = samples

    def __len__(self):
        return self._samples.shape[0]

    def __getitem__(self, ind):
        return self._samples[ind]

    @property
    def dates(self) -> List[datetime.date]:
        return [
            self._start + datetime.timedelta(days=i)
            for i in range(self._samples.shape[0])
        ]

    @property
    def daily_change(self) -> np.ndarray:
        return np.squeeze(np.pad(np.diff(self._samples), (1, 0)))

    def _local_regression(self, window: int, log_domain: bool,
                          order: int) -> List[LeastSquares]:
        '''Performs a series of local least-squares on the time series.

        This performs a series of local ordinary least squares analysis on the
        time series.  The results can then be used to compute attributes such
        as the (approximate) derivative or to filter the time series.

        Parameters
        ----------
        window : int
            size of the sliding window, in days, used for the local least
            squares
        log_domain : bool
            perform the estimation in the log-domain
        order : int, optional
            the order of the polynomial used for the regression; defaults
            to '1', which assumes the contents of the window are approximately
            linear

        Returns
        -------
        list of :class:`LeastSquares`
            a list of :class:`LeastSquares` regression estimates at each
            element in the time series.
        '''
        if log_domain:
            x = np.log(self._samples)
        else:
            x = self._samples

        if window < 3:
            raise ValueError('Window size must be at least three days.')

        N = len(self)
        least_squares = []
        for i in range(N):
            i_min = max(0, i - window // 2)
            i_max = min(N - 1, i + window // 2) + 1
            least_squares.append(LeastSquares(np.arange(i_min, i_max),
                                              x[i_min:i_max],
                                              order))

        return least_squares

    def smoothed(self, window: int, log_domain: bool,
                 order: int = 1) -> np.ndarray:
        '''Return a smoothed version of the time series.

        Parameters
        ----------
        window : int
            size of the sliding window, in days, used for the smoothing
        log_domain : bool
            perform the smoothing in the log-domain
        order : int, optional
            the order of the polynomial used for the smoothing; defaults
            to '1', which assumes the contents of the window are approximately
            linear

        Returns
        -------
        np.ndarray
            a ``N``-length array containing the smoothed time series
        '''
        output = np.zeros((len(self),))
        regressions = self._local_regression(window, log_domain, order)

        ls: LeastSquares
        for i, ls in enumerate(regressions):
            output[i] = ls.value(i)

        if log_domain:
            output = np.exp(output)

        return output

    def slope(self, window: int, order: int = 1,
              confidence: float = 0.95) -> np.ndarray:
        '''Estimate the slope at any given point in the time series.

        Parameters
        ----------
        window : int
            size of the sliding window, in days, used in the slope estimate
        order : int, optional
            the order of the polynomial used for the slope estimation; defaults
            to '1', which assumes the contents of the window are approximately
            linear
        confidence : float, optional
            the desired confidence interval, which defaults to 95%

        Returns
        -------
        numpy.ndarray
            a :math:`N \\times 3`` array containing the slope and 95%
            confidence interval, e.g. each row is ``(slope, upper_ci,
            lower_ci)``
        '''
        output = np.zeros((len(self), 3))
        regressions = self._local_regression(window, False, order)

        ls: LeastSquares
        for i, ls in enumerate(regressions):
            weights = ls.weights
            cv = ls.confidence(confidence)
            t0 = np.array([i])

            output[i, 0] = evalpoly(derivative(weights), t0)
            output[i, 1] = evalpoly(derivative(weights + cv), t0)
            output[i, 2] = evalpoly(derivative(weights - cv), t0)

        return output

    def percent_change(self, window: int, order: int = 1,
                       confidence: float = 0.95) -> np.ndarray:
        '''Estimate the day-over-day percent change.

        Parameters
        ----------
        window : int
            size of the sliding window, in days, used in the slope estimate
        order : int, optional
            the order of the polynomial used for the slope estimation; defaults
            to '1', which assumes the contents of the window are approximately
            linear
        confidence : float, optional
            the desired confidence interval, which defaults to 95%

        Returns
        -------
        numpy.ndarray
            a :math:`N \\times 3`` array containing the percent change and 95%
            confidence interval, e.g. each row is ``(slope, upper_ci,
            lower_ci)``
        '''
        output = np.zeros((len(self), 3))
        regressions = self._local_regression(window, True, order)

        ls: LeastSquares
        for i, ls in enumerate(regressions):
            weights = ls.weights
            cv = ls.confidence(confidence)
            t0 = np.array([i])

            output[i, 0] = evalpoly(derivative(weights), t0)
            output[i, 1] = evalpoly(derivative(weights + cv), t0)
            output[i, 2] = evalpoly(derivative(weights - cv), t0)

        # Convert into percent change by converting from the log-domain and
        # subtracting by one.
        output = np.exp(output) - 1
        return output

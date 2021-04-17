import datetime
from typing import List

import numpy as np

from .least_squares import LeastSquares
from .. import filters
from .._types import Datum


class TimeSeries:
    '''Represent a set of time series data

    Attributes
    ----------
    label : str
        a label used to describe the time series; it will default to the
        field used to generate the time series.
    dates : list of :class:`datetime.date` instances
        list of dates the time series represents
    daily_change : np.ndarray
        a convenience accessor to obtain the day-to-day changes via a finite
        difference
    daily_growth : np.ndarray
        the amount of growth in the time series, defined as
        ``daily_change[n]/daily_change[n-1]``
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
        self.label = field

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

    @property
    def daily_growth(self) -> np.ndarray:
        delta_x = self.daily_change
        current_delta_x = delta_x[1:]
        previous_delta_x = delta_x[:-1]

        # The growth value can only be computed if the previous day's change is
        # non-zero.
        valid = previous_delta_x > 0
        undefined = np.logical_and(current_delta_x > 0, previous_delta_x < 1)

        # Compute the growth only where it's well-defined.
        daily_growth = np.ones_like(current_delta_x)
        daily_growth[valid] = current_delta_x[valid] / previous_delta_x[valid]
        daily_growth[undefined] = np.nan

        return np.pad(daily_growth, (1, 0), constant_values=1)

    def local_regression(self, window: int, log_domain: bool = False,
                         order: int = 1) -> List[LeastSquares]:
        '''Performs a series of local least-squares on the time series.

        This performs a series of local ordinary least squares analysis on the
        time series.  The results can then be used to compute attributes such
        as the (approximate) derivative or to filter the time series.

        Parameters
        ----------
        window : int
            size of the sliding window, in days, used for the local least
            squares
        log_domain : bool, optional
            perform the estimation in the log-domain; defaults to ``False``
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

import datetime
from typing import List, Union

import numpy as np

from .least_squares import LeastSquares
from .. import filters
from .._types import Cases, CaseTesting

Datum = Union[Cases, CaseTesting]


class TimeSeries:
    '''Represent some time series data and apply some processing to it.

    Attributes
    ----------
    dates : list of :class:`datetime.date` instances
        list of dates the time series represents
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

    def slope(self, window: int, log_domain: bool) -> np.ndarray:
        '''Estimate the slope at any given point in the time series.

        Parameters
        ----------
        window : int
            size of the sliding window used in the slope estimate
        log_domain : bool
            compute the slope via the log-domain rather than the original
            domain

        Returns
        -------
        numpy.ndarray
            a :math:`3 \\times N`` array containing the slope and 95%
            confidence interval
        '''
        if log_domain:
            x = np.log10(self._samples)
        else:
            x = self._samples

        if window < 3:
            raise ValueError('Window size must be at least three days.')

        N = len(self)
        for i in range(N):
            i_min = max(0, i - window // 2)
            i_max = min(N - 1, i + window // 2) + 1

            ls = LeastSquares(np.arange(i_min, i_max), x[i_min:i_max], order=2)

            # TODO: Complete this

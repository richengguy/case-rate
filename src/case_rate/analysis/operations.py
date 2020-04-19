import numpy as np

from .least_squares import LeastSquares, derivative, evalpoly
from .timeseries import TimeSeries


__all__ = [
    'smooth',
    'estimate_slope',
    'percent_change'
]


def smooth(ts: TimeSeries, window: int, log_domain: bool,
           order: int = 1) -> np.ndarray:
    '''Return a smoothed version of a time series.

    Parameters
    ----------
    ts: :class:`TimeSeries`
        time series
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
    output = np.zeros((len(ts),))
    regressions = ts.local_regression(window, log_domain, order)

    ls: LeastSquares
    for i, ls in enumerate(regressions):
        output[i] = ls.value(i)

    if log_domain:
        output = np.exp(output)

    return output


def estimate_slope(ts: TimeSeries, window: int, order: int = 1,
                   confidence: float = 0.95) -> np.ndarray:
    '''Estimate the slope at any given point in a time series.

    Parameters
    ----------
    ts: :class:`TimeSeries`
        time series
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
    output = np.zeros((len(ts), 3))
    regressions = ts.local_regression(window, False, order)

    ls: LeastSquares
    for i, ls in enumerate(regressions):
        weights = ls.weights
        cv = ls.confidence(confidence)
        t0 = np.array([i])

        output[i, 0] = evalpoly(derivative(weights), t0)
        output[i, 1] = evalpoly(derivative(weights + cv), t0)
        output[i, 2] = evalpoly(derivative(weights - cv), t0)

    return output


def percent_change(ts: TimeSeries, window: int, order: int = 1,
                   confidence: float = 0.95) -> np.ndarray:
    '''Estimate the day-over-day percent change.

    Parameters
    ----------
    ts: :class:`TimeSeries`
        time series
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
    output = np.zeros((len(ts), 3))
    regressions = ts.local_regression(window, True, order)

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

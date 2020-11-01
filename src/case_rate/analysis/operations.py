import numpy as np
import scipy.signal

from .least_squares import LeastSquares, derivative, evalpoly
from .timeseries import TimeSeries


__all__ = [
    'smooth',
    'estimate_slope',
    'percent_change',
    'growth_factor'
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


def growth_factor(ts: TimeSeries, window: int, order: int = 1,
                  confidence: float = 0.95) -> np.ndarray:
    '''Estimate the exponential growth factor of the time series.

    The growth factor calculate assumes that the time series is describing a
    monotonic function such as a cumulative count.  This means the finite
    differences are always greater than or equal to zero.  Negative values are
    filtered out prior to the calculation.

    Parameters
    ----------
    ts: :class:`TimeSeries`
        time series
    window : int
        size of the sliding window, in days
    order : int, optional
        the order of the polynomial used for the regression; defaults to '1',
        which assumes the contents of the window are approximately linear
    confidence : float, optional
        the desired confidence interval, which defaults to 95%

    Returns
    -------
    numpy.ndarray
        a :math:`N \\times 3`` array containing the growth factor and 95%
        confidence interval, e.g. each row is ``(slope, upper_ci,
        lower_ci)``
    '''
    if order != 1:
        raise ValueError('Order must be "1".')

    N = len(ts)
    changes = ts.daily_change
    output = np.zeros((len(ts), 3))
    output[:] = np.nan

    if window < 3:
        raise ValueError('Window size must be at least three days.')

    for i in range(N):
        # Select the filtering window.  The 'daily changes' is returned as an
        # array, not as a TimeSeries, so this is being done directly in this
        # loop.
        i_min = max(0, i - window // 2)
        i_max = min(N - 1, i + window // 2) + 1

        x = changes[i_min:i_max]
        t = np.arange(i_min, i_max)

        '''
        x[n] = x[0] a^n
        log(x[n]) = log(x[0]a^n)
                  = log(x[0]) + log(a^n)
                  = log(x[0]) + log(a)*n
        '''

        # If all values in the window are '0' then the growth rate is, by
        # definition, also '0' because nothing's happening.
        if np.all(x == 0):
            output[i, :] = 0
            continue

        # Determine if there are any negative values.  Those may come from a
        # number of sources, such as corrections being applied onto the time
        # series.  If all values are negative then no growth rate can be
        # calculated.
        is_negative = x < 0
        if np.all(is_negative):
            continue

        # Similarly, there must enough values to calculate a least squares fit.
        valid = np.logical_not(is_negative)
        if valid.sum() < order+2:
            continue

        # Remove the invalid values and centre the window so that the centre
        # corresponds to 'n = 0'.  A small non-zero value is added to make it
        # possible to take the log of 'x' without any numerical issues.
        x = x[valid]
        t = t[valid]

        log_x = np.log(x + 1e-10)

        # Compute the least squares regression, getting the weights and
        # confidence interval.
        ls = LeastSquares(t, log_x, order)
        weights = ls.weights
        cv = ls.confidence(confidence)

        # The regression will find log(x[n]) = b_0 + b_1*n, where b_1 is the
        # estimate of log(a).
        output[i, 0] = np.exp(weights[1])
        output[i, 1] = np.exp(weights[1] + cv[1])
        output[i, 2] = np.exp(weights[1] - cv[1])

    return output

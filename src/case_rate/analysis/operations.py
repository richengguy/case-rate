import numpy as np

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


def _sequence_growth_factor(sequence: np.ndarray, window: int) -> np.ndarray:
    '''Calculate the exponential growth factor for an array.

    Parameters
    ----------
    sequence : np.ndarray
        a 1D array containing a sequency potentially undergoing exponential
        growth
    window : int
        width of the filtering window

    Returns
    -------
    np.ndarray
        estimated growth factor at each point in the sequence
    '''
    N = sequence.shape[0]
    output = np.zeros_like(sequence, dtype=np.float)
    output[:] = np.nan

    for i in range(N):
        i_min = max(0, i - window // 2)
        i_max = min(N - 1, i + window // 2) + 1

        x = sequence[i_min:i_max]
        t = np.arange(i_min, i_max)

        # If all values in the window are less than '0.5' then the growth rate
        # is, by definition, '0' because nothing's happening.  The value may be
        # smoothed, so this assumes that a value of '0.5' should be rounded
        # down to '0'.
        if np.all(x < 0.5):
            output[i] = 0
            continue

        # Determine if there are any negative values.  Those may come from a
        # number of sources, such as corrections being applied onto the time
        # series.  If all values are negative then no growth rate can be
        # calculated.
        is_negative = x < 0
        if np.all(is_negative):
            continue

        # Similarly, there must enough values to calculate a least squares fit.
        # Since this is a linear fit, that means 3 points (can work with 2, but
        # 3 is better).
        valid = np.logical_not(is_negative)
        if valid.sum() < 3:
            continue

        # Remove the invalid values and centre the window so that the centre
        # corresponds to 'n = 0'.
        x = x[valid]
        t = t[valid]

        # Add a small non-zero value when converting to log to allow it to work
        # with windows where some days don't change.
        log_x = np.log(x + 1e-10)

        # The regression will find log(x[n]) = b_0 + b_1*n, where b_1 is the
        # estimate of log(a).
        ls = LeastSquares(t, log_x, 1)
        output[i] = np.exp(ls.weights[1])

    return output


def growth_factor(ts: TimeSeries, window: int, order: int = 1,
                  confidence: float = 0.95) -> np.ndarray:
    '''Estimate the exponential growth factor of the time series.

    The growth factor is calculated from the LOESS regression provided by
    :meth:`estimate_slope`.  The three LOESS curves, i.e. the best fit and the
    upper and lower confidence interval curves, are used to estimate three
    equivalent growth factor curves.

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
        confidence interval, e.g. each row is ``(slope, upper_ci, lower_ci)``
    '''
    if window < 3:
        raise ValueError('Window size must be at least three days.')

    slopes = estimate_slope(ts, window, order, confidence)
    output = np.zeros_like(slopes)

    for i in range(slopes.shape[1]):
        output[:, i] = _sequence_growth_factor(slopes[:, i], window)

    # Set the upper/lower CI curves to zero if the best fit curve is zero.  The
    # results are meaningless in this case because there wasn't enough data to
    # do the calculation.
    best_fit = output[:, 0]
    confidence_intervals = output[:, 1:]
    confidence_intervals[best_fit == 0, :] = 0

    # The intervals curves will have different growth factor curves, so they
    # need to be sorted to be consistent with the idea of an upper/lower bound.
    is_swapped = np.argmin(confidence_intervals, 1) != 0

    if np.any(is_swapped):
        for i, swapped in enumerate(is_swapped):
            if not swapped:
                continue

            value = confidence_intervals[i, 0]
            confidence_intervals[i, 0] = confidence_intervals[i, 1]
            confidence_intervals[i, 1] = value

    output[:, 1:] = confidence_intervals
    return output

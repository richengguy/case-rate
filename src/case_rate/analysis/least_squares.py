import numpy as np
import scipy.stats


def _prep_array(array: np.ndarray) -> np.ndarray:
    '''Prepares the input array for processing.

    Parameters
    ----------
    array : np.ndarray
        input array
    '''
    if array.ndim == 1:
        array = np.reshape(array, (array.shape[0], 1))
    elif array.ndim > 2 or array.shape[1] != 1:
        raise ValueError('Input array must be Nx1.')

    return array.copy()


def derivative(b: np.ndarray) -> np.ndarray:
    '''Compute the derivative of a polynomial.

    Computing the derivative of a polynomial, given it's weights, is
    straightforward due to the fact that

    ..math::

        \\frac{d}{dx}x^n = n x^{n-1}.

    Therefore, given a polynomial of the form

    ..math::
        x(t) = b_0 + \\sum_{i=1}^k b_i t^i,

    then its derivative is

    ..math::

        \\frac{x(t)}{dt} = \\sum_{i=1}^{k} i b_i t^{i-1}.

    Parameters
    ----------
    b : np.ndarray
        a ``k``-length vector containing the input polynomial

    Returns
    -------
    np.ndarray
        a ``k-1``-length vector with the updated weights for the polynomial's
        derivative
    '''
    if b.ndim == 1:
        b = b[:, np.newaxis]
    return b[1:, 0] * np.arange(1, b.shape[0])


def evalpoly(b: np.ndarray, t: np.ndarray) -> np.ndarray:
    '''Evaluates a polynomial for the given weights and times.

    The polynomial being evaluated takes the form

    ..math::

        x(t) = b_0 + \\sum_{i=1}^{k} b_i t^i,

    where :math:`k` is the polynomial order.

    Parameters
    ----------
    b : np.ndarray
        an array containing the weights of a k-th order polynomial
    t : np.ndarray
        a vector of times to evaluate the polynomal at

    Returns
    -------
    np.ndarray
        another vector, same size as ``t``, with the values of the evaluated
        polynomial
    '''
    n = np.arange(b.shape[0])
    tn = np.vstack(list(np.power(ti, n) for ti in t))
    return tn @ b


class LeastSquares:
    '''Compute a least-squares line fit to some data.

    This implements a simple curve fitting proceduring using ordinary least
    squares.  It allows for estimating the slope of a theoretical curve given
    noisy data.  Given a polynomial of the form

    ..math::

        x(t) = b_0 + \\sum_{i=1}^{k}b_i t^i,

    the regression will find the values of
    :math:`\\vec{b} = \\begin{bmatrix}b_0 & b_1 & \\dots & b_k\\end{bmatrix}^T`
    such that the error

    ..math::

        E = \\sum_j \\left\\{ y_j - x(t_j) \\right\\}^2,

    where  :math:``\\vec{y} = \\begin{bmatrix} y_0 & y_1 & \\dots & y_{N-1} \\end{bmatrix}`,
    is minimized.

    Attributes
    ----------
    weights : np.ndarray
        a :math:`K \\times 1` vector with the estimated model weights
    rmse : float
        the model's root-mean-squared error
    noise_variance : float
        an estimate of the noise variance, calculated from the model residuals
    '''  # noqa: E501
    def __init__(self, times: np.ndarray, values: np.ndarray, order: int = 1):
        '''
        Parameters
        ----------
        times : np.ndarray
            list of sample indices as a :math:`N \\times 1` array
        values : np.ndarray
            list of measured values as a :math:`N \\times 1` array
        order : int, optional
            the degree of the polynomial being fit, defaults to '1' or a
            straight line
        '''
        values = _prep_array(values)
        times = _prep_array(times)

        if values.shape[0] != times.shape[0]:
            raise ValueError('Input data must have same size.')

        if values.shape[0] <= order + 1:
            raise ValueError('Number of samples must be greater tha one plus '
                             'polynomial order.')

        # Matrix sizes.
        N = values.shape[0]
        K = order + 1

        # Construct the linear system.
        y = values
        X = times.repeat(K, axis=1)

        for j in range(K):
            X[:, j] = X[:, j]**j

        print(X)
        print(X.transpose() @ X)

        # Compute the weights using the normal equations.
        self._weights = np.linalg.pinv(X) @ y

        # Compute the confidence of fit.
        residuals = (y - X @ self._weights)**2
        ssr = residuals.sum()
        covar = np.linalg.inv(X.transpose() @ X)

        self._rmse = np.sqrt(ssr/N)
        self._noise = ssr / (N - K)
        self._variances = np.diag(covar) * self._noise
        self._dof = N - K

    @property
    def weights(self) -> np.ndarray:
        return self._weights

    @property
    def rmse(self) -> float:
        return self._rmse

    @property
    def noise_variance(self) -> float:
        return self._noise

    @property
    def weight_variance(self) -> float:
        return self._variances

    def confidence_interval(self, alpha: float = 0.95) -> np.ndarray:
        '''Compute the confidence interval on the least squares solution.

        The confidence interval is found using the two-sided student's t-test.
        The upper and lower limits for the confidence interval can be found by
        adding this value to the computed weights.

        Parameters
        ----------
        alpha : float, optional
            the confidence interval, defaults to 0.95 (95%)

        Returns
        -------
        np.ndarray
            a :math:`K \\times 1` array with the confidence value
        '''
        c = scipy.stats.t.ppf((1 + alpha)/2, self._dof)
        ci = c*np.sqrt(self._variances)
        return ci[:, np.newaxis]

    def value(self, time: np.ndarray) -> np.ndarray:
        '''Obtain the value from the least-squares regressor.

        Parameters
        ----------
        time : np.ndarray or float
            the input time

        Returns
        -------
        float
            function value at the specified time
        '''
        if isinstance(time, (float, int)):
            time = np.array([time])
        return evalpoly(self._weights, time)

    def slope(self, time: np.ndarray) -> np.ndarray:
        '''Compute the derivative at time 't'.

        This computation is straightfoward as the derivative of polynomial
        curve is easy to derive from its weights.  If the input polynomal is

        ..math::
            x(t) = b_0 + \\sum_{i=1}^k b_i t^i,

        then the derivative is

        ..math::

            \\frac{x(t)}{dt} = \\sum_{i=1}^{k} i b_i t^{i-1}.

        Parameters
        ----------
        time : np.ndarray or float
            the input times

        Returns
        -------
        np.ndarray
            the value of the first derivative evaluated at the specified times
        '''
        if isinstance(time, (float, int)):
            time = np.array([time])
        weights = self._weights[1:, 0] * np.arange(1, self._weights.shape[0])
        return evalpoly(weights, time)

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


class LeastSquares:
    '''Compute a least-squares line fit to some data.

    This implements a simple curve fitting proceduring using ordinary least
    squares.  It allows for estimating the slope of a theoretical curve given
    noisy data.

    Attributes
    ----------
    weights : np.ndarray
        a :math:`K \\times 1` vector with the estimated model weights
    rmse : float
        the model's root-mean-squared error
    noise_variance : float
        an estimate of the noise variance, calculated from the model residuals
    '''
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

        # Compute the weights using the normal equations.
        self._weights = np.linalg.pinv(X) @ y

        # Compute the confidence of fit.
        residuals = (y - X @ self._weights)**2
        covar = np.linalg.inv(X.transpose() @ X)

        self._rmse = np.sqrt(residuals.sum()/N)
        self._noise = np.sum(residuals*residuals) / (N - K - 1)
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
        return c*np.sqrt(self._variances)

    def value(self, time: float) -> float:
        '''Obtain the value from the least-squares regressor.

        Parameters
        ----------
        time : float
            the input time

        Returns
        -------
        float
            function value at the specified time
        '''
        n = np.arange(self._weights.shape[0])
        t = np.power(time, n)
        return t[np.newaxis, :] @ self._weights

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
        self._rmse = np.sqrt(residuals.sum()/N)
        self._variance = np.sum(residuals*residuals) / (N - K - 1)

    @property
    def weights(self) -> np.ndarray:
        return self._weights

    @property
    def rmse(self) -> float:
        return self._rmse

    @property
    def variance(self) -> float:
        return self._variance

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

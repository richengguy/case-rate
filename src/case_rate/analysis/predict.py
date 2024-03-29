from typing import Optional, Tuple

import numpy as np

from .least_squares import evalpoly, LeastSquares
from .operations import estimate_growth
from .timeseries import TimeSeries


class DailyCasesPredictor:
    '''Predict the number of daily cases by modelling the growth factor.

    The predictor using a simple linear model to track how the growth factor
    changes over time.  The factor itself, which is equivalent to the effective
    reproductive number, changes depending on population dynamics.  The
    predictor uses the N of the past N+L days, where 'L' is the number of days
    where the case count may be subject to reporting lags.
    '''
    def __init__(self, analysis_window: int = 14, reporting_lag: int = 3,
                 model_order: int = 1, filter_window: int = -1):
        '''Initialize the predictor.

        Parameters
        ----------
        analysis_window : int, optional
            the number of days used for modelling the "local" growth factor, by
            default 14
        reporting_lag : int, optional
            the number of past days that may be subject to a reporting lag, by
            default 3
        model_order : int, optional
            the order of the regression order, by default 1 or linear
        filter_window : int, optional
            size of the filter window used to smooth the input time series, by
            default is '-1', meaning it is set to the analysis window size
        '''
        self.analysis_window = analysis_window
        self.model_order = model_order
        self.reporting_lag = reporting_lag
        self.filter_window = filter_window if filter_window > 0 else analysis_window

        self._model: Optional[LeastSquares] = None
        self._training_indices = np.zeros((0,))
        self._validation_indices = np.zeros((0,))

        self._training_samples = None
        self._validation_samples = None

    @property
    def is_trained(self) -> bool:
        '''bool: Has the model been trained?'''
        return self._model is not None

    @property
    def training_samples(self) -> np.ndarray:
        '''ndarray: The samples used to train the model.'''
        if self._training_samples is None:
            raise RuntimeError('Model has not yet been trained.')
        return self._training_samples

    @property
    def validation_samples(self) -> np.ndarray:
        '''ndarray: The samples used to validate the model.'''
        if self._validation_samples is None:
            raise RuntimeError('Model has not yet been trained.')
        return self._validation_samples

    @property
    def training_window(self) -> np.ndarray:
        '''ndarray: The time series indices used for training the model.'''
        return self._training_indices

    @property
    def validation_window(self) -> np.ndarray:
        '''ndarray: The time series indices for the reporting lag (also act as a validation set).'''
        return self._validation_indices

    @property
    def parameters(self) -> np.ndarray:
        '''ndarray: The estimated model parameters.'''
        if self._model is None:
            raise RuntimeError('Model has not yet been trained.')
        return self._model.weights

    def growth_model(self, days: int = 0) -> np.ndarray:
        '''Return the growth model over a set number of days.

        Parameters
        ----------
        days : int, optional
            the number of days, by default 0 so that it uses the default
            analysis window

        Returns
        -------
        np.ndarray
            the growth model

        Raises
        ------
        RuntimeError
            if the model hasn't been trained
        '''
        if self._model is None:
            raise RuntimeError('Model has not yet been trained.')

        if days <= 0:
            days = self.analysis_window

        return evalpoly(self.parameters, np.arange(days))

    def confidence_interval(self, days: int = 0, alpha: float = 0.95) -> np.ndarray:
        '''Return the confidence interval for the growth model.

        Parameters
        ----------
        days : int, optional
            the number of days, by default 0 so that it uses the default
            analysis window

        Returns
        -------
        np.ndarray
            the confidence interval as an :math:`N \\times 2` array

        Raises
        ------
        RuntimeError
            if the model hasn't been trained
        '''
        if self._model is None:
            raise RuntimeError('Model has not yet been trained.')

        if days <= 0:
            days = self.analysis_window

        model = self.growth_model(days)
        confidence = self._model.confidence_fit(np.arange(days), alpha)
        return np.hstack((model + confidence, model - confidence))

    def prediction_interval(self, days: int = 0, alpha: float = 0.95) -> np.ndarray:
        '''Return the prediction interval for the growth model.

        Parameters
        ----------
        days : int, optional
            the number of days, by default 0 so that it uses the default
            analysis window

        Returns
        -------
        np.ndarray
            the prediction interval as an :math:`N \\times 2` array

        Raises
        ------
        RuntimeError
            if the model hasn't been trained
        '''
        if self._model is None:
            raise RuntimeError('Model has not yet been trained.')

        if days <= 0:
            days = self.analysis_window

        model = self.growth_model(days)
        prediction = self._model.prediction_fit(np.arange(days), alpha)
        return np.hstack((model + prediction, model - prediction))

    def train(self, ts: TimeSeries) -> Tuple[float, float]:
        '''Train the predictor on some time series.

        Parameters
        ----------
        ts : TimeSeries
            time series contain case rate data

        Returns
        -------
        solution_error : float
            the standard error on the growth factor regression model
        validation_error : float
            the RMS error on how well the model predicts the samples in the
            lag window
        '''
        N = len(ts)
        self._training_indices = np.arange(
            N-self.analysis_window-self.reporting_lag,
            N-self.reporting_lag)
        self._validation_indices = np.arange(N-self.reporting_lag, N)

        daily_growth = estimate_growth(ts, self.filter_window)
        training_samples = daily_growth[self._training_indices]

        # NOTE: This uses zero-based indices so that the regression is relative
        # to the training window.  This avoids having to specify the date when
        # preforming a prediction.  It's always relative to the end of the
        # time series.
        indices = np.arange(self.analysis_window)
        self._model = LeastSquares(indices, training_samples, order=self.model_order)
        self._training_samples = training_samples
        self._validation_samples = daily_growth[self._validation_indices]

        daily_cases = ts.daily_change[-(self.reporting_lag+1):]
        prediction, _, _ = self.predict(daily_cases[0], self.reporting_lag)

        residuals = prediction - daily_cases
        validation_error = np.sqrt(np.sum(residuals**2)/len(residuals))

        return self._model.standard_error, validation_error

    def predict(self, current_count: float, num_days: int = 14,
                alpha: float = 0.95) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        '''Predict the next 'N' days, given the current case count.

        The prediction always includes the reporting lag so that the first
        :attr:`reporting_lag` samples will be in the past.

        Parameters
        ----------
        current_count : float
            the current case count (i.e. the initial condition)
        num_days : int, optional
            the number of days to predict, by default 14`

        Returns
        -------
        daily_cases : np.ndarray
            a ``num_days+1`` length array with the prediction ``num_days`` into
            the future, starting with the **first** validation sample
        confidence : np.ndarray
            a two-column array containing the predicted cases uses the
            upper/lower confidence intervals on the growth model
        indices : np.ndarray
            the set of indices that the prediction corresponds to

        Raises
        ------
        ValueError
            if the model has not been trained
        '''
        if self._model is None:
            raise ValueError('The model has not yet been trained.')

        indices = np.arange(num_days) + self.analysis_window - 1
        growth = self._model.value(indices)
        confidence = self._model.prediction_fit(indices, alpha)

        upper_bound = growth + confidence
        lower_bound = growth - confidence

        predicted_cases = np.zeros((num_days+1,))
        bounds = np.zeros((num_days+1, 2))

        predicted_cases[0] = current_count
        bounds[0, :] = current_count
        for n in range(num_days):
            predicted_cases[n+1] = growth[n]*predicted_cases[n]
            bounds[n+1, 0] = upper_bound[n]*bounds[n, 0]
            bounds[n+1, 1] = lower_bound[n]*bounds[n, 1]

        series_indices = np.arange(num_days+1) + self._training_indices[-1]
        return predicted_cases, bounds, series_indices

import numpy as np

import torch.nn
import torch.optim

from .network import PrefilterNetwork, SimpleRecurrentNetwork


class PoissonLikelihood(torch.nn.Module):
    '''Implements the log-likelihood under a Poisson distribution.

    The likelihood is calculated using the log-Gamma approximation,

    ..math::

        L(k;\\lambda) = k \\ln{\\lambda'} - \\lambda' - \\ln{\\Gamma(k + 1)}

    where

    ..math::

        \\lambda' = \\lambda + \\epsilon

    and :math:`\\epsilon = 10^{-6}` to avoid a NaN when :math:`\\lambda = 0`.
    '''
    def __init__(self):
        super().__init__()

    def forward(self, lmbda: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
        '''Compute the value of the loss function.

        Parameters
        ----------
        lmbda : torch.Tensor
            the estimated value of :math:`\\lambda`
        k : torch.Tensor
            the observed value

        Returns
        -------
        torch.Tensor
            the log-likelihood of :math:`k \\approx \\mathrm{P(\\lambda)}`
        '''
        lp = lmbda + 1e-6
        return k * torch.log(lp) - lp - torch.lgamma(k + 1)


class SquaredError(torch.nn.Module):
    '''Implements a standard squared error loss.

    The reason for this versus PyTorch's built-in MSE is to allow for some
    customization.
    '''
    def __init__(self):
        super().__init__()

    def forward(self, lmbda: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
        '''Compute the value of the loss function.

        Parameters
        ----------
        lmbda : torch.Tensor
            the estimated value of :math:`\\lambda`
        k : torch.Tensor
            the observed value

        Returns
        -------
        torch.Tensor
            :math:`(k - \\lambda)^2`
        '''
        return torch.pow(lmbda - k, 2)


class Model:
    '''A simple predictive model to estimate counts from a time series.

    Attributes
    ----------
    prefilter : :class:`PrefilterNetwork`
        the "prefiltering" network that applies a CNN onto the timeseries and
        performing some initial dimensionality reduction
    predictor : :class:`SimpleRecurrentNetwork`
        a *very* simple RNN that will attempt to predict the next value in the
        input sequence, given the output from the prefilter
    '''
    def __init__(self, features: int, hidden: int = 64,
                 learning_rate: float = 0.01):
        '''
        Parameters
        ----------
        features : int
            the dimensionality of each sample in the time series
        hidden : int, optional
            size of the hidden layer within the RNN, default is 64
        learning_rate : int, optional
            learning rate used for the model's optimizer
        '''
        self.prefilter = PrefilterNetwork(features)
        self.predictor = SimpleRecurrentNetwork(features, hidden)
        self.optim = torch.optim.AdamW([
            {'params': self.prefilter.parameters()},
            {'params': self.predictor.parameters()}
        ], lr=learning_rate)

    def train(self, timeseries: np.ndarray) -> float:
        '''Train the model on the provided timeseries.

        Parameters
        ----------
        timeseries : np.ndarray
            a :math:`(F, N)` array of :math:`N` samples with :math:`F` features
            each

        Returns
        -------
        float
            the estimated loss for this timeseries
        '''
        timeseries = self._prep_input(timeseries)
        self.optim.zero_grad()

        likelihood = PoissonLikelihood()
        loss = 0

        filtered = timeseries[:, 0]
        hidden = self.predictor.default_state()
        for i in range(1, timeseries.shape[1]-1):
            filtered = self.prefilter(timeseries[:, i], filtered)
            lmbda, hidden = self.predictor(filtered, hidden)
            loss += -likelihood(lmbda, timeseries[:, i+1])

        loss.backward()
        self.optim.step()

        return loss.item() / (timeseries.shape[1]-2)

    def _predict_next(self, timeseries: torch.Tensor) -> torch.Tensor:
        '''Predict the next sample in the timeseries.

        Parameters
        ----------
        timeseries : torch.Tensor
            input timeseries

        Returns
        -------
        torch.Tensor
            predicted sample
        '''
        filtered = timeseries[:, 0]
        hidden = self.predictor.default_state()
        for i in range(1, timeseries.shape[1]):
            filtered = self.prefilter(timeseries[:, i], filtered)
            lmbda, hidden = self.predictor(filtered, hidden)
        return lmbda

    def reconstruct(self, timeseries: np.ndarray) -> np.ndarray:
        '''Reconstructs the sequence using the trained model.

        Parameters
        ----------
        timeseries : np.ndarray
            a :math:`(F, N)` array of :math:`N` samples with :math:`F` features
            each

        Returns
        -------
        np.ndarray
            the model's reconstruction
        '''
        with torch.no_grad():
            timeseries = self._prep_input(timeseries)
            filtered = timeseries.clone()
            for i in range(1, timeseries.shape[1]):
                filtered[:, i] = self.prefilter(timeseries[:, i],
                                                filtered[:, i-1])

            storage = torch.empty_like(filtered)
            hidden = self.predictor.default_state()
            for i in range(filtered.shape[1]):
                lmbda, hidden = self.predictor(filtered[0, i], hidden)
                storage[:, i] = lmbda

        output = storage.numpy()
        return output.squeeze()

    def _prep_input(self, timeseries: np.ndarray) -> torch.Tensor:
        '''Prepares the external NumPy format data for processing.

        Parameters
        ----------
        timeseries : np.ndarray
            input NumPy array

        Returns
        -------
        torch.Tensor
            prepared tensor object
        '''
        timeseries = torch.tensor(timeseries)

        if timeseries.ndim == 1:
            timeseries.unsqueeze_(0)

        if timeseries.dtype != torch.float32:
            timeseries = timeseries.float()

        return timeseries

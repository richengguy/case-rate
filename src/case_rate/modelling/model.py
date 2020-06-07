import random

import numpy as np

import torch
import torch.nn
import torch.optim

from .._types import PathLike
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
    def __init__(self, features: int, lookahead: int, hidden: int = 64,
                 learning_rate: float = 0.01):
        '''
        Parameters
        ----------
        features : int
            the dimensionality of each sample in the time series
        lookahead : int
            the number of samples ahead (i.e. days) that the predictor should
            try to predict based on past data
        hidden : int, optional
            size of the hidden layer within the RNN, default is 64
        learning_rate : int, optional
            learning rate used for the model's optimizer
        '''
        self._features = features
        self._hidden = hidden
        self._learning_rate = learning_rate
        self._lookahead = lookahead

        self.prefilter = PrefilterNetwork(features)
        self.predictor = SimpleRecurrentNetwork(features, hidden)
        self.optim = torch.optim.AdamW([
            {'params': self.prefilter.parameters()},
            {'params': self.predictor.parameters()}
        ], lr=learning_rate)

    def train(self, timeseries: np.ndarray) -> float:
        '''Train the model on the provided timeseries.

        The training step will randomly select a "start time", which is some
        point within the sequence to start the prediction.  The start time will
        always been in the range :math:`[2W, N-W]`, where :math:`W` is the
        desired look-ahead period and :math:`N` is the total sequence length.

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

        self.prefilter.train()
        self.predictor.train()
        self.optim.zero_grad()

        likelihood = PoissonLikelihood()
        loss = 0

        # Prime the network by running through between 2*W and (N-W) samples.
        N = timeseries.shape[1]
        start = random.randint(2*self._lookahead, N - self._lookahead)

        filtered = timeseries[:, 0]
        hidden = self.predictor.default_state()
        for i in range(1, start):
            filtered = self.prefilter(timeseries[:, i], filtered)
            lmbda, hidden = self.predictor(filtered, hidden)

        # Compute the loss for the last calculated value of lambda.
        loss += -likelihood(lmbda, timeseries[:, i])

        # Now compute the loss, trying to predict the next 'W' samples.
        for i in range(start, start + self._lookahead):
            predicted = torch.poisson(lmbda)
            filtered = self.prefilter(predicted, filtered)
            lmbda, hidden = self.predictor(filtered, hidden)
            loss += -likelihood(lmbda, timeseries[:, i])

        loss.backward()
        self.optim.step()

        return loss.item() / self._lookahead

    def predict(self, timeseries: np.ndarray,
                sample: bool = False) -> np.ndarray:
        '''Make a prediction given the input time series.

        Parameters
        ----------
        timeseries : np.ndarray
            a :math:`(F, N)` array of :math:`N` samples with :math:`F` features
            each
        sample : bool, optional
            if ``True`` then return each sample as
            :math:`k \\sim \\mathrm{Pois}(\\lambda)`, otherwise return the
            expected value, :math:`\\lambda`, which is the default behaviour

        Returns
        -------
        np.ndarray
            the prediction as a :math:`(F, W)` array, where :math:`W` is the
            size of the look-ahead (i.e. prediction) window
        '''
        with torch.no_grad():
            self.prefilter.eval()
            self.predictor.eval()

            timeseries = self._prep_input(timeseries)

            # Prepare the filter/predictor by running through the existing
            # data.
            filtered = timeseries[:, 0]
            hidden = self.predictor.default_state()
            for i in range(1, timeseries.shape[1]):
                filtered = self.prefilter(timeseries[:, i], filtered)
                lmbda, hidden = self.predictor(filtered, hidden)

            # Now predict what the next 'W' samples look like.
            output = torch.empty(timeseries.shape[0], self._lookahead)
            for i in range(0, self._lookahead):
                predicted = torch.poisson(lmbda)

                if sample:
                    output[:, i] = predicted
                else:
                    output[:, i] = lmbda

                filtered = self.prefilter(predicted, filtered)
                lmbda, hidden = self.predictor(filtered, hidden)

        output = output.numpy()
        return output.squeeze()

    def filter(self, timeseries: np.ndarray) -> np.ndarray:
        '''Runs the tuned IIR pre-filter on the time series.

        This can be useful to see what the network thinks is the optimal
        filtering needed to perform the prediction.

        Parameters
        ----------
        timeseries : np.ndarray
            a :math:`(F, N)` array of :math:`N` samples with :math:`F` features
            each

        Returns
        -------
        np.ndarray
            the filtered timeseries
        '''
        self.prefilter.eval()
        self.predictor.eval()
        with torch.no_grad():
            timeseries = self._prep_input(timeseries)
            filtered = timeseries.clone()
            for i in range(1, timeseries.shape[1]):
                filtered[:, i] = self.prefilter(timeseries[:, i],
                                                filtered[:, i-1])

        filtered = filtered.numpy()
        return filtered.squeeze()

    def save(self, path: PathLike):
        '''Save the model to disk.

        The model is saved using the :func:`torch.save` function.  The
        resulting file is in the standard Python pickle format.

        Parameters
        ----------
        path : path-like object
            a string or :class:`Path` with the name of the output file; if it
            exists then it will be overwritten
        '''
        model = {
            'prefilter': self.prefilter.state_dict(),
            'predictor': self.predictor.state_dict(),
            'optimizer': self.optim.state_dict(),
            'configuration': {
                'features': self._features,
                'lookahead': self._lookahead,
                'hidden': self._hidden,
                'learning_rate': self._learning_rate
            }
        }
        torch.save(model, path)

    @staticmethod
    def load(path: PathLike) -> 'Model':
        '''Load a model from a PyTorch '.pth' file.

        This uses :func:`torch.load`, which performs a standard unpickling
        operation on the data in the file.

        Parameters
        ----------
        path : path-like object
            path to the model file

        Returns
        -------
        :class:`Model`
            the loaded model instance
        '''
        serialized = torch.load(path)
        model = Model(**serialized['configuration'])
        model.prefilter.load_state_dict(serialized['prefilter'])
        model.predictor.load_state_dict(serialized['predictor'])
        model.optim.load_state_dict(serialized['optimizer'])
        return model

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

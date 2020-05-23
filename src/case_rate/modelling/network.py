import math
from typing import Tuple

import numpy as np

import torch
import torch.nn
import torch.nn.functional as F


class PrefilterNetwork(torch.nn.Module):
    '''A single-layer CNN designed to filter a timeseries signal.

    Attributes
    ----------
    weight : torch.Tensor
        the model's weights tensor
    bias : torch.Tensor
        the model's bias vector
    '''
    def __init__(self, window: int, features: int):
        '''
        Parameters
        ----------
        window : int
            size of the filtering window
        features : int
            number of features at each sample
        '''
        super().__init__()
        if window < 1:
            raise ValueError('Window size must be greater than zero.')
        if features < 1:
            raise ValueError('Dimensionality must be greater than zero.')

        filter_size = (1, features, window)

        # Create the model parameters.
        self.weight = torch.nn.Parameter(torch.empty(filter_size,
                                                     requires_grad=True))
        self.bias = torch.nn.Parameter(torch.empty(1, requires_grad=True))

        # Initialize the weights.
        k = math.sqrt(1/(features*window))
        torch.nn.init.kaiming_uniform_(self.weight, nonlinearity='relu')
        torch.nn.init.uniform_(self.bias, -k, k)

    def forward(self, timeseries: torch.Tensor) -> torch.Tensor:
        '''Apply a forward pass of the network.

        The filter compresses the time series input features from :math:`F`
        dimensions to :math:`1`.  It also doesn't use any padding, so the
        output length is smaller than the input.

        Parameters
        ----------
        timeseries : torch.Tensor
            the input :math:`F \\times N` time series

        Returns
        -------
        torch.Tensor
            the filtered time series of length :math:`1 \\times (N - W - 1)`
        '''
        timeseries = timeseries.unsqueeze(0)
        filtered = F.conv1d(timeseries, self.weight, self.bias)
        output = F.relu(filtered)
        return output.squeeze(0)


class SimpleRecurrentNetwork(torch.nn.Module):
    '''Implements a simple RNN.

    Attributes
    ----------
    input_layer : module object
        the layer that processing the input to the RNN
    output_layer : module object
        the layer that generates the output of the RNN
    window : int, read-only
        the size of the filtering window expected by the network
    features : int, read-only
        the number of features for each sample
    '''
    def __init__(self, window: int, features: int, hidden: int = 64,
                 batch: int = 1):
        '''
        Parameters
        ----------
        window : int
            the number of samples required by the network before it can output
            a result
        features : int
            the number of features per sample, which defines the dimensionality
            of the input space
        hidden : int
            number of neurons in the hidden state (layer); default is 64
        batch : int
            the input batch size; default is '1'

        Raises
        ------
        ValueError
            if the window size or dimensionality is less than 1
        '''
        super().__init__()
        if window < 1:
            raise ValueError('Window size must be greater than zero.')
        if features < 1:
            raise ValueError('Dimensionality must be greater than zero.')

        input_size = window*features + hidden
        output_size = features

        self._window = window
        self._dims = features
        self._hidden = hidden
        self._batch = batch

        self.input_layer = torch.nn.Linear(input_size, hidden)
        self.output_layer = torch.nn.Linear(hidden, output_size)

    @property
    def window(self) -> int:
        return self._window

    @property
    def features(self) -> int:
        return self._dims

    def forward(self,  sample: torch.Tensor,
                hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        '''Apply the forward transform.

        Parameters
        ----------
        sample : torch.Tensor
            the input sequence of size `(N, features, window)`
        hidden : torch.Tensor
            the RNN's hidden state vector; this should be obtained using the
            :meth:`default_state` method

        Returns
        -------
        output : torch.Tensor
            the model's generated output
        '''
        sample = sample.reshape(-1, self._window*self._dims)
        concat = torch.cat((sample, hidden), 1)
        hidden = torch.tanh(self.input_layer(concat))
        output = F.softplus(self.output_layer(hidden))
        return output, hidden

    def default_state(self, initial_value: float = 1e-6):
        '''Creates a new initial state vector.

        This creates the initial conditions for the network.  It generates a
        vector with a very small, but non-zero, norm.

        Parameters
        ----------
        initial_value : float
            the initial value of the hidden state vector; defaults to it having
            a norm of 1e-6
        '''
        log_nrm = np.log(initial_value)
        log_N = np.log(self._hidden)
        log_init = 0.5*(2.0*log_nrm - log_N)
        return np.exp(log_init)*torch.ones((self._batch, self._hidden))

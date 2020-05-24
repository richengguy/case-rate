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
    features : int, readonly
        dimensionality of the input feature space
    window : int, readonly
        size of the filtering window
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
        self._features = features
        self._window = window

        # Enable passthrough mode if the number of features is '1', since the
        # CNN isn't going any sort of feature reduction.
        self.pass_through = features == 1

        # Create the model parameters.
        self.weight = torch.nn.Parameter(torch.empty(filter_size,
                                                     requires_grad=True))
        self.bias = torch.nn.Parameter(torch.empty(1, requires_grad=True))

        # Initialize the weights.
        k = math.sqrt(1/(features*window))
        torch.nn.init.kaiming_uniform_(self.weight, nonlinearity='relu')
        torch.nn.init.uniform_(self.bias, -k, k)

    @property
    def features(self) -> int:
        return self._features

    @property
    def kernel_size(self) -> int:
        if self.pass_through:
            return 1
        else:
            return self._window

    def forward(self, timeseries: torch.Tensor) -> torch.Tensor:
        '''Apply a forward pass of the network.

        The filter compresses the time series input features from :math:`F`
        dimensions to :math:`1`.  It also doesn't use any padding, so the
        output length is smaller than the input.

        Parameters
        ----------
        timeseries : torch.Tensor
            the input :math:`(F, N)` time series

        Returns
        -------
        torch.Tensor
            the filtered time series of length :math:`(1, N - W - 1)`
        '''
        if self.pass_through:
            return timeseries

        timeseries = timeseries.unsqueeze(0)
        filtered = F.conv1d(timeseries, self.weight, self.bias)
        output = F.relu(filtered)
        return output.squeeze(0)


class SimpleRecurrentNetwork(torch.nn.Module):
    '''Implements a simple RNN.

    This is meant to be used in conjunction with the :class:`PrefilterNetwork`.

    Attributes
    ----------
    weight_input : torch.Tensor
        the weights used to map the RNN's input onto space spanned by the
        hidden vector
    weight_hidden : torch.Tensor
        the weights applied onto the RNN's hidden vector
    weight_output : torch.Tensor
        the weights applied to map the hidden vector onto the output
    bias_input : torch.Tensor
        the bias vector for the RNN's input layer
    bias_output : torch.Tensor
        the bias vector for the RNN's output layer
    features : int, readonly
        the dimensionality of the output space
    hidden_size : int, readonly
        the dimensionality of the hidden space
    '''
    def __init__(self, features: int, hidden: int = 64):
        '''
        Parameters
        ----------
        features : int
            the dimensionality of the *output* space; it must be the same as
            the input to the prefilter
        hidden : int
            number of neurons in the hidden state (layer); default is 64
        '''
        super().__init__()
        if features < 1:
            raise ValueError('Dimensionality must be greater than zero.')

        self._features = features
        self._hidden = hidden

        # Create the weights.
        weight_input = torch.empty((hidden, 1), requires_grad=True)
        weight_hidden = torch.empty((hidden, hidden), requires_grad=True)
        weight_output = torch.empty((features, hidden), requires_grad=True)
        bias_input = torch.empty((hidden, 1), requires_grad=True)
        bias_output = torch.empty((features, 1), requires_grad=True)

        # Assign them to the parameters.
        self.weight_input = torch.nn.Parameter(weight_input)
        self.weight_hidden = torch.nn.Parameter(weight_hidden)
        self.weight_output = torch.nn.Parameter(weight_output)
        self.bias_input = torch.nn.Parameter(bias_input)
        self.bias_output = torch.nn.Parameter(bias_output)

        # Do the initialization.
        gain = torch.nn.init.calculate_gain('tanh')
        torch.nn.init.xavier_uniform_(self.weight_input, gain)
        torch.nn.init.xavier_uniform_(self.weight_hidden, gain)
        torch.nn.init.xavier_uniform_(self.weight_output)

        k1 = math.sqrt(1/hidden)
        k2 = math.sqrt(1/features)
        torch.nn.init.uniform_(self.bias_input, -k1, k1)
        torch.nn.init.uniform_(self.bias_output, -k2, k2)

    @property
    def features(self) -> int:
        return self._features

    @property
    def hidden_size(self) -> int:
        return self._hidden

    def forward(self,  sample: torch.Tensor,
                hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        '''Apply the forward transform.

        Parameters
        ----------
        sample : torch.Tensor
            the input (scalar value)
        hidden : torch.Tensor
            the RNN's hidden state vector; this should be obtained using the
            :meth:`default_state` method

        Returns
        -------
        output : torch.Tensor
            the model's generated output
        '''
        X = self.weight_input * sample
        Y = self.weight_hidden @ hidden
        hidden = torch.tanh(X + Y + self.bias_input)
        output = F.softplus(self.weight_output @ hidden + self.bias_output)
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
        return np.exp(log_init)*torch.ones(self._hidden, 1)

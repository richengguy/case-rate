import torch
import torch.nn
import torch.nn.functional as F


class SimpleRecurrentNetwork(torch.nn.Module):
    '''Implements a simple RNN.

    Attributes
    ----------
    hidden_state : torch.Tensor
        a tensor containing the RNN's hidden state
    input_layer : module object
        the layer that processing the input to the RNN
    output_layer : module object
        the layer that generates the output of the RNN
    '''
    def __init__(self, window: int, features: int, hidden: int = 64):
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

        self.hidden_state = torch.zeros(1, self._hidden)
        self.input_layer = torch.nn.Linear(input_size, hidden)
        self.output_layer = torch.nn.Linear(hidden, output_size)

    def forward(self, sample: torch.Tensor) -> torch.Tensor:
        '''Apply the forward transform.

        Parameters
        ----------
        sample : torch.Tensor
            the input sequence of size `(N, window, features)`

        Returns
        -------
        output : torch.Tensor
            the model's generated output
        '''
        view = sample.view((-1, self._window*self._dims))
        concat = torch.cat((view, self.hidden_state), 1)
        hidden = torch.tanh(self.input_layer(concat))
        output = F.relu(self.output_layer(hidden))

        self.hidden_state = hidden
        return output

    def reset(self):
        '''Reset the RNN's internal state.

        This is done by zeroing out the hidden state.  It *does not* change the
        model weights.
        '''
        self.hidden_state = torch.zeros(1, self.hidden_state)

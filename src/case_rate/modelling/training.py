import numpy as np
import torch
import torch.optim

from .recurrent_model import SimpleRecurrentNetwork


class Trainer:
    '''Train the given model on some training data.'''
    def __init__(self, model: SimpleRecurrentNetwork,
                 learning_rate: float = 1e-3):
        '''
        Parameters
        ----------
        model : SimpleRecurrentNetwork
            the model being trained
        learning_rate : float
            the optimizer's learning rate, default is 0.001
        '''
        self._model = model
        self._optim = torch.optim.Adam(model.parameters(), lr=learning_rate)

    def train(self, data: np.ndarray) -> float:
        '''Train the model on the given sample

        Parameters
        ----------
        data : np.ndarray
            input sample data, stored as a `(features, num_samples)` matrix

        Returns
        -------
        float
            the negative log-likelihood after training the model on this sample
        '''
        if data.ndim == 1:
            data = data[np.newaxis, :]

        features, num_samples = data.shape
        window_size = self._model.window
        tensor_size = (1, features, num_samples + window_size - 1)

        # Generate the tensor that will be used during training.
        tensor = torch.zeros(tensor_size)
        tensor[0, :, 0:window_size] = torch.tensor(data[:, 0])
        tensor[0, :, window_size:] = torch.tensor(data[:, 1:])

        # Train the model by getting it to predict the next value in an integer
        # sequence, under the assumption that the data are integer-valued and
        # represent counts.
        hidden = self._model.default_state()
        self._model.train()
        self._optim.zero_grad()

        loglikelihood = 0
        for i in range(window_size, num_samples-1):
            i_min = i - window_size
            window = tensor[:, :, i_min:i]

            # Get the estimates of the Poisson 'lambda' parameter and the next
            # actual value.
            lambda_, hidden = self._model(window, hidden)
            k = tensor[:, :, i+1]

            # Compute the likelihood of the predicted lambda for the actual
            # value.
            loglikelihood += k*torch.log(lambda_) - lambda_ - torch.lgamma(k+1)

        neglikelihood = -loglikelihood / num_samples
        neglikelihood.backward()
        self._optim.step()

        return neglikelihood.item()

    def predict(self, data: np.ndarray) -> np.ndarray:
        '''Run the model on the given data.'''
        if data.ndim == 1:
            data = data[np.newaxis, :]

        features, num_samples = data.shape
        window_size = self._model.window
        tensor_size = (1, features, num_samples + window_size - 1)

        # Generate the tensor that will be used during training.
        tensor = torch.zeros(tensor_size)
        tensor[0, :, 0:window_size] = torch.tensor(data[:, 0])
        tensor[0, :, window_size:] = torch.tensor(data[:, 1:])

        # Train the model by getting it to predict the next value in an integer
        # sequence, under the assumption that the data are integer-valued and
        # represent counts.
        hidden = self._model.default_state()
        self._model.eval()

        output = [0]*(window_size)
        for i in range(window_size, num_samples-1):
            i_min = i - window_size
            window = tensor[:, :, i_min:i]

            # Get the estimates of the Poisson 'lambda' parameter and the next
            # actual value.
            lambda_, hidden = self._model(window, hidden)

            output.append(lambda_.item())

        return np.array(output)

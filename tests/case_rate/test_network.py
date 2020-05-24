import pytest

try:
    import torch
except ImportError:
    pytest.skip('PyTorch must be installed to run network tests.',
                allow_module_level=True)

from case_rate.modelling.network import PrefilterNetwork
from case_rate.modelling.network import SimpleRecurrentNetwork


class TestPrefilterNetwork:
    def test_single_sample(self):
        signal = torch.zeros(1, 5)
        signal[0, 0] = 1.0

        network = PrefilterNetwork(1)
        assert network.features == 1
        assert network.alpha == 0.95

        filtered = network(signal[0, 1], signal[0, 0])
        assert filtered.ndim == 1
        assert filtered.shape[0] == 1
        assert torch.isclose(filtered, torch.Tensor([0.05]))

    def test_correct_padding(self):
        signal = torch.zeros(3, 50)
        network = PrefilterNetwork(3)
        assert network.features == 3
        assert network.alpha.allclose(torch.tensor([0.95, 0.95, 0.95]))

        filtered = network(signal[:, 1], signal[:, 0])
        assert filtered.ndim == 1
        assert filtered.shape[0] == 3

    def test_bad_init(self):
        # Invalid number of features.
        with pytest.raises(ValueError):
            PrefilterNetwork(0)

        # Invalid initial alpha.
        with pytest.raises(ValueError):
            PrefilterNetwork(1, initial_alpha=-1)

        with pytest.raises(ValueError):
            PrefilterNetwork(1, initial_alpha=2)

        PrefilterNetwork(1, 0.5)


class TestSimpleRecurrentNetwork:
    def test_forward_single_feature(self):
        signal = torch.zeros(1, 5)
        network = SimpleRecurrentNetwork(1, 8)

        hidden = torch.zeros_like(network.default_state())
        for i in range(5):
            out, internal = network(signal[0, i], hidden)

            assert internal.shape == hidden.shape

            assert out.ndim == 2
            assert out.shape[0] == 1
            assert out.shape[1] == 1

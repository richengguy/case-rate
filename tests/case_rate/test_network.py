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
        network = PrefilterNetwork(5, 1)
        assert network.pass_through
        assert network.features == 1
        assert network.kernel_size == 1

        filtered = network(signal)
        assert filtered.ndim == 2
        assert filtered.shape[0] == 1
        assert filtered.shape[1] == 5

    def test_correct_padding(self):
        signal = torch.zeros(3, 50)
        network = PrefilterNetwork(5, 3)
        assert not network.pass_through
        assert network.features == 3
        assert network.kernel_size == 5

        filtered = network(signal)
        assert filtered.ndim == 2
        assert filtered.shape[0] == 1
        assert filtered.shape[1] == 46

    def test_bad_init(self):
        with pytest.raises(ValueError):
            PrefilterNetwork(0, 1)

        with pytest.raises(ValueError):
            PrefilterNetwork(1, 0)

        PrefilterNetwork(1, 1)


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

import pytest

try:
    import torch
except ImportError:
    pytest.skip('PyTorch must be installed to run network tests.',
                allow_module_level=True)

from case_rate.modelling.network import PrefilterNetwork


class TestPrefilterNetwork:
    def test_single_sample(self):
        signal = torch.zeros(1, 5)
        network = PrefilterNetwork(5, 1)
        filtered = network(signal)
        assert filtered.ndim == 2
        assert filtered.shape[0] == 1
        assert filtered.shape[1] == 1

    def test_correct_padding(self):
        signal = torch.zeros(3, 50)
        network = PrefilterNetwork(5, 3)
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

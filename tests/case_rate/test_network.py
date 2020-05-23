import pytest

try:
    import torch
except ImportError:
    pytest.skip('PyTorch must be installed to run network tests.',
                allow_module_level=True)

from case_rate.modelling.network import PrefilterNetwork

class TestPrefilterNetwork:
    def test_correct_padding(self):
        signal = torch.zeros(3, 50)
        network = PrefilterNetwork(5, 3)
        filtered = network(signal)
        print(filtered.shape)
        assert filtered.ndim == 2
        assert filtered.shape[0] == 1
        assert filtered.shape[1] == 46

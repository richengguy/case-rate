import numpy as np
import pytest

from case_rate.analysis.least_squares import LeastSquares


class TestLeastSquares:
    def test_simple_regression_linear(self):
        t = np.arange(10)
        x = 0.5*t + 1

        ls = LeastSquares(t, x)
        assert np.isclose(ls.weights[0], 1.0)
        assert np.isclose(ls.weights[1], 0.5)
        assert np.isclose(ls.value(0.5), 1.25)

    def test_simple_regression_quadratic(self):
        t = np.arange(10)
        x = 2*t**2 + 0.3*t + 0.5

        ls = LeastSquares(t, x, order=2)
        assert np.isclose(ls.weights[0], 0.5)
        assert np.isclose(ls.weights[1], 0.3)
        assert np.isclose(ls.weights[2], 2.0)
        assert np.isclose(ls.value(0.5), 1.15)

    def test_reject_insufficient_samples(self):
        t = np.arange(2)
        x = 2*t**2 + 0.3*t + 0.5
        with pytest.raises(ValueError):
            LeastSquares(t, x, order=2)

    def test_reject_different_sizes(self):
        t = np.arange(5)
        x = 0.5*t + 1

        with pytest.raises(ValueError):
            LeastSquares(t, x[0:3])

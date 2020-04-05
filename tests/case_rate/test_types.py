import datetime
from case_rate._types import Cases, CaseTesting

import pytest


class TestTypes:
    def test_sum_cases_same_region(self):
        a = Cases(
            date=datetime.date(1234, 5, 6),
            province='province',
            country='country',
            confirmed=10,
            resolved=5,
            deceased=0
        )
        b = Cases(
            date=datetime.date(1234, 5, 6),
            province='province',
            country='country',
            confirmed=5,
            resolved=2,
            deceased=0
        )

        c = a + b
        assert c.date == datetime.date(1234, 5, 6)
        assert c.province == 'province'
        assert c.country == 'country'
        assert c.confirmed == 15
        assert c.resolved == 7
        assert c.deceased == 0

    def test_sum_cases_different_region(self):
        a = Cases(
            date=datetime.date(1234, 5, 6),
            province='First Province',
            country='First Country',
            confirmed=10,
            resolved=5,
            deceased=0
        )
        b = Cases(
            date=datetime.date(1234, 5, 6),
            province='Second Province',
            country='Second Country',
            confirmed=5,
            resolved=2,
            deceased=0
        )

        c = a + b
        assert c.date == datetime.date(1234, 5, 6)
        assert c.province == 'aggr'
        assert c.country == 'aggr'
        assert c.confirmed == 15
        assert c.resolved == 7
        assert c.deceased == 0

    def test_cannot_sum_cases_different_dates(self):
        a = Cases(
            date=datetime.date(1234, 5, 6),
            province='province',
            country='country',
            confirmed=10,
            resolved=5,
            deceased=0
        )
        b = Cases(
            date=datetime.date(1234, 10, 10),
            province='province',
            country='country',
            confirmed=5,
            resolved=2,
            deceased=0
        )

        with pytest.raises(ValueError):
            a + b

    def test_sum_case_tests_same_region(self):
        a = CaseTesting(
            date=datetime.date(1234, 5, 6),
            province='province',
            country='country',
            tested=10,
            under_investigation=1
        )

        c = a + a
        assert c.date == datetime.date(1234, 5, 6)
        assert c.province == 'province'
        assert c.country == 'country'
        assert c.tested == 20
        assert c.under_investigation == 2

    def test_sum_case_tests_different_region(self):
        a = CaseTesting(
            date=datetime.date(1234, 5, 6),
            province='First Province',
            country='First Country',
            tested=10,
            under_investigation=1
        )
        b = CaseTesting(
            date=datetime.date(1234, 5, 6),
            province='Second Province',
            country='Second Country',
            tested=10,
            under_investigation=1
        )

        c = a + b
        assert c.date == datetime.date(1234, 5, 6)
        assert c.province == 'aggr'
        assert c.country == 'aggr'
        assert c.tested == 20
        assert c.under_investigation == 2

    def test_cannot_sum_tests_different_dates(self):
        a = CaseTesting(
            date=datetime.date(1234, 5, 6),
            province='First Province',
            country='First Country',
            tested=10,
            under_investigation=1
        )
        b = CaseTesting(
            date=datetime.date(1234, 10, 10),
            province='Second Province',
            country='Second Country',
            tested=10,
            under_investigation=1
        )

        with pytest.raises(ValueError):
            a + b

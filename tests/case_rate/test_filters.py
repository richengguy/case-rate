import datetime
from typing import List

import pytest

from case_rate import filters
from case_rate._types import Cases, CaseTesting


class TestFilters:
    def test_sum_cases(self):
        cases: List[Cases] = []
        for i in range(10):
            cases.append(Cases(
                date=datetime.date(1234, 5, 6),
                province='province',
                country='country',
                confirmed=1,
                resolved=0,
                deceased=0
            ))

        summed = filters.sum_by_date(cases)
        assert len(summed) == 1
        assert summed[0].confirmed == 10

    def test_sum_casetesting(self):
        tests: List[CaseTesting] = []
        for i in range(10):
            tests.append(CaseTesting(
                date=datetime.date(1234, 5, 6),
                province='province',
                country='country',
                tested=1,
                under_investigation=0
            ))

        summed = filters.sum_by_date(tests)
        assert len(summed) == 1
        assert summed[0].tested == 10

    def test_summing_mixed_lists_raise_exception(self):
        mixed = [
            CaseTesting(
                date=datetime.date(1234, 5, 6),
                province='province',
                country='country',
                tested=1,
                under_investigation=0
            ),
            Cases(
                date=datetime.date(1234, 5, 6),
                province='province',
                country='country',
                confirmed=1,
                resolved=0,
                deceased=0
            )
        ]

        with pytest.raises(TypeError):
            filters.sum_by_date(mixed)

    def test_sum_cases_different_days(self):
        cases: List[Cases] = []
        for i in range(10):
            cases.append(Cases(
                date=datetime.date(1234, 5, i+1),
                province='province',
                country='country',
                confirmed=1,
                resolved=0,
                deceased=0
            ))

        summed = filters.sum_by_date(cases)
        assert len(summed) == 10

        case: Cases
        for i, case in enumerate(summed):
            assert case.date.day == i+1
            assert case.confirmed == 1

    def test_sum_cases_mixed(self):
        cases: List[Cases] = []
        for i in range(10):
            cases.append(Cases(
                date=datetime.date(1234, 5, i+1),
                province='a',
                country='a',
                confirmed=1,
                resolved=0,
                deceased=0
            ))
            cases.append(Cases(
                date=datetime.date(1234, 5, i+1),
                province='b',
                country='b',
                confirmed=1,
                resolved=0,
                deceased=0
            ))

        summed = filters.sum_by_date(cases)
        assert len(cases) == 20
        assert len(summed) == 10

        case: Cases
        for i, case in enumerate(summed):
            assert case.date.day == i+1
            assert case.province == 'aggr'
            assert case.country == 'aggr'
            assert case.confirmed == 2

    def test_select_by_country(self):
        cases = [
            Cases(
                date=datetime.date(1234, 5, 6),
                province='a',
                country='a',
                confirmed=1,
                resolved=0,
                deceased=0
            ),
            Cases(
                date=datetime.date(1234, 5, 6),
                province='b',
                country='b',
                confirmed=1,
                resolved=0,
                deceased=0
            )
        ]

        selected = filters.select_by_country(cases, 'a')
        assert len(selected) == 1
        assert selected[0].country == 'a'

        selected = filters.select_by_country(cases, 'b')
        assert len(selected) == 1
        assert selected[0].country == 'b'

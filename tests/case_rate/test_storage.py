import datetime

from case_rate.storage import (Storage, InputSource, Cases, CaseTesting,
                               _generate_select)


class MockedSource(InputSource):
    @classmethod
    def name(cls):
        return 'TestSource'

    def details(self):
        return 'Input source used to test the Storage class.'

    def url(self):
        return 'http://127.0.0.1'

    def cases(self):
        date = datetime.date(1234, 5, 6)
        yield Cases(
            date=date,
            province='',
            country='',
            confirmed=2,
            resolved=1,
            deceased=0)

    def testing(self):
        date = datetime.date(1234, 5, 6)
        yield CaseTesting(
            date=date,
            province='',
            country='',
            tested=10,
            under_investigation=5)


class CaseOnlySource(InputSource):
    @classmethod
    def name(cls):
        return 'CaseOnlySource'

    def details(self):
        return 'Input source with only cases, no testing data.'

    def url(self):
        return 'http://127.0.0.1'

    def cases(self):
        date = datetime.date(1234, 5, 6)
        yield Cases(
            date=date,
            province='',
            country='',
            confirmed=2,
            resolved=1,
            deceased=0)


class RegionalSource(InputSource):
    @classmethod
    def name(cls):
        return 'RegionalSource'

    def details(self):
        return 'Input source with regions.'

    def url(self):
        return 'http://127.0.0.1'

    def cases(self):
        date = datetime.date(1234, 5, 6)

        provinces = ['', '', 'province', 'province']
        countries = ['', 'country', '', 'country']

        for provice, country in zip(provinces, countries):
            yield Cases(
                date=date,
                province=provice,
                country=country,
                confirmed=2,
                resolved=1,
                deceased=0)

    def testing(self):
        date = datetime.date(1234, 5, 6)

        provinces = ['', '', 'province', 'province']
        countries = ['', 'country', '', 'country']

        for provice, country in zip(provinces, countries):
            yield CaseTesting(
                date=date,
                province=provice,
                country=country,
                tested=10,
                under_investigation=5)


class TestStorageInternals:
    def test_date_insert(self):
        sample_date = datetime.date(1234, 5, 6)
        with Storage() as storage:
            storage._conn.execute(
                'INSERT INTO testing (date) VALUES (?)',
                (sample_date,))

            row = storage._conn.execute('SELECT * FROM testing').fetchone()
            assert row['date'].year == 1234
            assert row['date'].month == 5
            assert row['date'].day == 6

    def test_generate_select(self):
        sql, rgn = _generate_select('table', ('a', 'b', 'c'))
        assert sql == 'SELECT a, b, c FROM table WHERE source == ?'
        assert len(rgn) == 0

        sql, rgn = _generate_select('table', ('a', 'b', 'c'), ('province', None))  # noqa: E501
        assert sql == 'SELECT a, b, c FROM table WHERE source == ? AND province == ?'  # noqa: E501
        assert len(rgn) == 1
        assert rgn[0] == 'province'

        sql, rgn = _generate_select('table', ('a', 'b', 'c'), (None, 'country'))  # noqa: E501
        assert sql == 'SELECT a, b, c FROM table WHERE source == ? AND country == ?'  # noqa: E501
        assert len(rgn) == 1
        assert rgn[0] == 'country'

        sql, rgn = _generate_select('table', ('a', 'b', 'c'), ('province', 'country'))  # noqa: E501
        assert sql == 'SELECT a, b, c FROM table WHERE source == ? AND province == ? AND country == ?'  # noqa: E501
        assert len(rgn) == 2
        assert rgn[0] == 'province'
        assert rgn[1] == 'country'


class TestStorage:
    def test_class_name(self):
        test_source = MockedSource()
        assert MockedSource.name() == 'TestSource'
        assert test_source.name() == MockedSource.name()

    def test_source_register(self):
        test_source = MockedSource()
        with Storage() as storage:
            assert storage._get_source(test_source.name()) is None

            ref = storage._register(test_source)
            assert ref.name == test_source.name()
            assert ref.details == test_source.details()
            assert ref.url == test_source.url()
            assert ref.source_id == 1

    def test_populate_full(self):
        sample_date = datetime.date(1234, 5, 6)
        test_source = MockedSource()
        with Storage() as storage:
            storage.populate(test_source)

            sources = storage.sources
            assert test_source.name() in sources
            assert sources[test_source.name()][0] == test_source.details()
            assert sources[test_source.name()][1] == test_source.url()

            cases = storage.cases('TestSource')
            assert len(cases) == 1
            assert cases[0].date == sample_date
            assert cases[0].confirmed == 2
            assert cases[0].resolved == 1
            assert cases[0].deceased == 0

            tests = storage.tests('TestSource')
            assert len(tests) == 1
            assert tests[0].date == sample_date
            assert tests[0].tested == 10
            assert tests[0].under_investigation == 5

    def test_populate_cases_only(self):
        sample_date = datetime.date(1234, 5, 6)
        test_source = CaseOnlySource()
        with Storage() as storage:
            storage.populate(test_source)

            cases = storage.cases('CaseOnlySource')
            assert len(cases) == 1
            assert cases[0].date == sample_date
            assert cases[0].confirmed == 2
            assert cases[0].resolved == 1
            assert cases[0].deceased == 0

            tests = storage.tests('CaseOnlySource')
            assert len(tests) == 0

    def test_select_region(self):
        test_source = RegionalSource()
        with Storage() as storage:
            storage.populate(test_source)

            assert len(storage.cases('RegionalSource')) == 4
            assert len(storage.cases('RegionalSource', province='province')) == 2  # noqa: E501
            assert len(storage.cases('RegionalSource', country='country')) == 2  # noqa: E501
            assert len(storage.cases('RegionalSource', country='country', province='province')) == 1  # noqa: E501

            assert len(storage.tests('RegionalSource')) == 4
            assert len(storage.tests('RegionalSource', province='province')) == 2  # noqa: E501
            assert len(storage.tests('RegionalSource', country='country')) == 2  # noqa: E501
            assert len(storage.tests('RegionalSource', country='country', province='province')) == 1  # noqa: E501

import datetime

from case_rate.storage import Storage, InputSource, Cases, CaseTesting


class MockedSource(InputSource):
    @property
    def name(self):
        return 'TestSource'

    @property
    def details(self):
        return 'Input source used to test the Storage class.'

    @property
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


class TestStorage:
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

    def test_source_register(self):
        test_source = MockedSource()
        with Storage() as storage:
            assert storage._get_source(test_source.name) is None

            ref = storage._register(test_source)
            assert ref.name == test_source.name
            assert ref.details == test_source.details
            assert ref.url == test_source.url
            assert ref.source_id == 1

    def test_populate(self):
        sample_date = datetime.date(1234, 5, 6)
        test_source = MockedSource()
        with Storage() as storage:
            storage.populate(test_source)

            sources = storage.sources
            assert test_source.name in sources
            assert sources[test_source.name][0] == test_source.details
            assert sources[test_source.name][1] == test_source.url

            cases = storage.all_cases('TestSource')
            assert len(cases) == 1
            assert cases[0].date == sample_date
            assert cases[0].confirmed == 2
            assert cases[0].resolved == 1
            assert cases[0].deceased == 0

            tests = storage.all_tests('TestSource')
            assert len(tests) == 1
            assert tests[0].date == sample_date
            assert tests[0].tested == 10
            assert tests[0].under_investigation == 5

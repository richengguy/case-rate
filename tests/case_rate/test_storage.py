import datetime

import pytest

from case_rate.storage import Storage, InputSource


class TestSource(InputSource):
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
        return

    @pytest.mark.skip('This isn\'t actually a test; pytest grabs it during test discovery.')  # noqa: E501
    def testing(self):
        return


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
        test_source = TestSource()
        with Storage() as storage:
            assert storage._get_source(test_source) is None

            ref = storage._register(test_source)
            assert ref.name == test_source.name
            assert ref.details == test_source.details
            assert ref.url == test_source.url
            assert ref.source_id == 1

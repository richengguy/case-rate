import datetime

from case_rate.storage import Storage


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

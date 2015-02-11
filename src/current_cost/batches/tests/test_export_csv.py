from json import dumps
import unittest
from datetime import datetime

from current_cost.batches.export_csv import ExportBatch
from os.path import join
import redis


__author__ = 'bruno'


class ExportBatchCsvTest(unittest.TestCase):
    def test_export_temp_csv_file(self):
        myredis = redis.Redis()
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T14:10:07', 'watt': 400, 'temperature':20.0, 'nb_data': 234}))
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T16:10:07', 'watt': 420, 'temperature':22.0, 'nb_data': 123}))

        filename = ExportBatch(date=datetime(2012, 12, 13)).create_csv_file()

        with open(filename, mode='r') as csv:
            self.assertEquals('date;nb_data;temperature;watt\n', csv.readline())
            self.assertEquals('2012-12-13T16:10:07;123;22.0;420\n', csv.readline())
            self.assertEquals('2012-12-13T14:10:07;234;20.0;400\n', csv.readline())

    def test_export_temp_csv_file_no_key_does_nothing(self):
        self.assertIsNone(ExportBatch(date=datetime(2012, 12, 14)).create_csv_file())

    def test_export_temp_csv_file_no_key_but_file_returns_file_name(self):
        batch = ExportBatch(date=datetime(2012, 12, 15))
        filename = join('/tmp','%s.csv' % batch.key)
        with open(filename, 'w') as file:
            file.writelines(['this;is;a;previous;temp;csv;file\n'])

        self.assertEquals(batch.create_csv_file(), filename)


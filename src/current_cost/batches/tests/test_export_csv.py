from json import dumps
from tempfile import mktemp
import unittest
from datetime import datetime
from current_cost.batches.export_csv import ExportBatch, DIR
from os.path import basename, join
import redis
from mockftp_server import FTPStubServer

__author__ = 'bruno'


class ExportBatchCsvTest(unittest.TestCase):
    def test_export_temp_csv_file(self):
        myredis = redis.Redis()
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T14:10:07', 'watt': 400, 'temperature':20.0, 'nb_data': 234}))
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T16:10:07', 'watt': 420, 'temperature':22.0, 'nb_data': 123}))

        filename = ExportBatch(date=datetime(2012, 12, 13)).create_csv_file()

        with open(filename, mode='r') as csv:
            self.assertEquals('date;watt;nb_data;temperature\n', csv.readline())
            self.assertEquals('2012-12-13T16:10:07;420;123;22.0\n', csv.readline())
            self.assertEquals('2012-12-13T14:10:07;400;234;20.0\n', csv.readline())

    def test_export_temp_csv_file_no_key_does_nothing(self):
        self.assertIsNone(ExportBatch(date=datetime(2012, 12, 14)).create_csv_file())

    def test_export_temp_csv_file_no_key_but_file_returns_file_name(self):
        batch = ExportBatch(date=datetime(2012, 12, 15))
        filename = join('/tmp','%s.csv' % batch.key)
        with open(filename, 'w') as file:
            file.writelines(['this;is;a;previous;temp;csv;file\n'])

        self.assertEquals(batch.create_csv_file(), filename)


class ExportBatchFtpSendTest(unittest.TestCase):
    def setUp(self):
        self.server = FTPStubServer(8998)
        self.server.run()

    def tearDown(self):
        self.server.stop()

    def test_send_ftp(self):
        filename = mktemp()
        with open(filename, 'w') as file:
            file.writelines(['this is a line in the file\n', 'this is another line in the file'])

        ExportBatch().ftp_send(filename, 'localhost', 8998, 'test', 'pass')

        self.assertEquals(self.server._interactions[:3], ['USER test\r\n', 'PASS pass\r\n', 'TYPE A\r\n'])
        self.assertEquals(self.server.files(join(DIR, basename(filename))), 'this is a line in the file\r\nthis is another line in the file' )

    def test_send_ftp_none_filename_does_nothing(self):
        ExportBatch().ftp_send(None)
        self.assertEquals(len(self.server._interactions), 0)



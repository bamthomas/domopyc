from json import dumps
from posixpath import join
import unittest
from datetime import datetime
import redis
from export_csv import ExportBatch

__author__ = 'bruno'

class RedisSubscribeLoopTest(unittest.TestCase):
    def test_export_temp_csv_file(self):
        myredis = redis.Redis()
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T14:10:07', 'watt': 400, 'temperature':20.0, 'nb_data': 234}))
        myredis.lpush('current_cost_2012-12-13', dumps({'date': '2012-12-13T16:10:07', 'watt': 420, 'temperature':22.0, 'nb_data': 123}))

        filename = ExportBatch(date=datetime(2012, 12, 13)).create_csv_file()

        with open(filename, mode='r') as csv:
            self.assertEquals('date;watt;nb_data;temperature\n', csv.readline())
            self.assertEquals('2012-12-13T16:10:07;420;123;22.0\n', csv.readline())
            self.assertEquals('2012-12-13T14:10:07;400;234;20.0\n', csv.readline())

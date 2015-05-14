from datetime import datetime
from json import dumps
import unittest
from subscribers.iso8601_json import Iso8601DateEncoder
import pymysql
from subscribers.sensor import current_cost

__author__ = 'bruno'


class MysqlAverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 2, 0)
        self.db = pymysql.connect(host='localhost', user='test', passwd='test', db='test')

        cursor = self.db.cursor()
        cursor.execute("drop table if EXISTS current_cost")
        cursor.close()

    def tearDown(self):
        self.db.close()

    def test_create_table_if_it_doesnot_exist(self):
        cursor = self.db.cursor()

        cursor.execute("show tables like 'current_cost'")
        current_cost_table = cursor.fetchall()
        self.assertEqual((), current_cost_table)

        current_cost.MysqlAverageMessageHandler(self.db, average_period_minutes=10)

        cursor.execute("show tables like 'current_cost'")
        current_cost_table = cursor.fetchall()
        self.assertEquals((('current_cost',),), current_cost_table)
        cursor.close()

    def test_average(self):
        message_handler = current_cost.MysqlAverageMessageHandler(self.db, average_period_minutes=10)
        message_handler.handle(dumps({'date': current_cost.now(), 'watt': 100, 'temperature': 20.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.nb_table_rows('current_cost'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 3, 0)
        message_handler.handle(dumps({'date': current_cost.now(), 'watt': 200, 'temperature': 30.0}, cls=Iso8601DateEncoder))
        self.assertEquals(0, self.nb_table_rows('current_cost'))

        current_cost.now = lambda: datetime(2012, 12, 13, 14, 10, 0, 1)
        message_handler.handle(dumps({'date': current_cost.now(), 'watt': 900, 'temperature': 10.0}, cls=Iso8601DateEncoder))

        self.assertEquals(1, self.nb_table_rows('current_cost'))
        cursor = self.db.cursor()
        cursor.execute("select timestamp, watt, minutes, nb_data, temperature from current_cost")
        rows = cursor.fetchall()
        self.assertEqual((datetime(2012, 12, 13, 14, 10, 0), 400, 10, 3, 20.0), rows[0])
        cursor.close()

    def nb_table_rows(self, table):
        with self.db:
            cursor = self.db.cursor()
            cursor.execute("select * from %s" % table)
            return len(cursor.fetchall())
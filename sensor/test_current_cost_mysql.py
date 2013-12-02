from _mysql import OperationalError
from datetime import datetime
import unittest
import MySQLdb
import current_cost

__author__ = 'bruno'


class MysqlAverageMessageHandlerTest(unittest.TestCase):
    def setUp(self):
        current_cost.now = lambda: datetime(2012, 12, 13, 14, 2, 0)
        self.db = MySQLdb.connect(host='localhost', user='test', passwd='test', db='test')
        with self.db:
            try:
                self.db.cursor().execute("drop table current_cost")
            except OperationalError as table_does_not_exist:
                pass


    def test_create_table_if_it_doesnot_exist(self):
        with self.db:
            cursor = self.db.cursor()

            cursor.execute("show tables like 'current_cost'")
            current_cost_table = cursor.fetchall()
            self.assertEqual((), current_cost_table)

            current_cost.MysqlAverageMessageHandler(self.db, average_period_minutes=10)

            cursor.execute("show tables like 'current_cost'")
            current_cost_table = cursor.fetchall()
            self.assertEquals((('current_cost',),), current_cost_table)

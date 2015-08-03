from datetime import datetime, timezone
from json import dumps
import unittest
import asyncio
import aiomysql
import asynctest
from domopyc.iso8601_json import Iso8601DateEncoder

from domopyc.subscribers import redis_toolbox
from domopyc.subscribers.mysql_toolbox import MysqlCurrentCostMessageHandler, MysqlTemperatureMessageHandler


class MysqlAverageMessageHandlerTest(asynctest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("drop table if EXISTS current_cost")
            yield from cur.close()

        redis_toolbox.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = MysqlCurrentCostMessageHandler(self.pool)

    @asyncio.coroutine
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_create_table_if_it_doesnot_exist(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()

            yield from cur.execute("show tables like 'current_cost'")
            current_cost_table = yield from cur.fetchall()
            self.assertEqual((('current_cost',),), current_cost_table)

            MysqlCurrentCostMessageHandler(self.pool, average_period_minutes=10)

            yield from cur.execute("show tables like 'current_cost'")
            current_cost_table = yield from cur.fetchall()
            self.assertEquals((('current_cost',),), current_cost_table)
            yield from cur.close()

    @asyncio.coroutine
    def test_save_event_mysql(self):
        with (yield from self.pool) as conn:
            now = datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)

            yield from self.message_handler.handle(
                dumps({'date': now, 'watt': 305.0, 'temperature': 21.4}, cls=Iso8601DateEncoder))

            table_rows = yield from self.nb_table_rows('current_cost')
            self.assertEquals(1, table_rows)

            cursor = yield from conn.cursor()
            yield from cursor.execute("select timestamp, watt, minutes, nb_data, temperature from current_cost")
            rows = yield from cursor.fetchall()
            self.assertEqual((datetime(2012, 12, 13, 14, 0, 7), 305, 0, 1, 21.4), rows[0])
            yield from cursor.close()

    def nb_table_rows(self, table):
        with (yield from self.pool) as conn:
            cursor = yield from conn.cursor()
            yield from cursor.execute("select * from %s" % table)
            allrows = yield from cursor.fetchall()
            return len(allrows)


class MysqlTemperatureMessageHandlerTest(unittest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("drop table if EXISTS test_temp")
            yield from cur.close()

        redis_toolbox.now = lambda: datetime(2012, 12, 13, 14, 2, 0, tzinfo=timezone.utc)
        self.message_handler = MysqlTemperatureMessageHandler(self.pool, 'test_temp')

    @asyncio.coroutine
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_save_event_mysql(self):
        with (yield from self.pool) as conn:
            now = datetime(2012, 12, 13, 14, 0, 7, tzinfo=timezone.utc)

            yield from self.message_handler.handle({'date': now, 'temperature': 21.4})

            cursor = yield from conn.cursor()
            yield from cursor.execute("select timestamp, temperature from test_temp")
            rows = yield from cursor.fetchall()
            self.assertEqual((datetime(2012, 12, 13, 14, 0, 7), 21.4), rows[0])
            yield from cursor.close()
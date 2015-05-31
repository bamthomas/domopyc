from datetime import datetime, timedelta, timezone
from json import dumps, loads
import asyncio
from unittest import TestCase
import aiohttp
import os
import aiomysql

from iso8601_json import Iso8601DateEncoder, with_iso8601_date
from subscribers.mysql_toolbox import MysqlAverageMessageHandler
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis
from web import domopyc_server
from web.domopyc_server import get_current_cost_data

__author__ = 'bruno'


class RedisGetDataOfDay(TestCase):
    @async_coro
    def setUp(self):
        os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/..')
        self.server = yield from domopyc_server.init(asyncio.get_event_loop())

        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        self.message_handler = MysqlAverageMessageHandler(self.pool)
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("truncate current_cost")


    @async_coro
    def tearDown(self):
        self.server.close()


    @async_coro
    def test_get_current_cost_history(self):
        domopyc_server.now = lambda: datetime(2015, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        message = lambda watt: {'date': domopyc_server.now(), 'watt': watt, 'minutes': 10, 'nb_data': 120, 'temperature': 20.2}
        yield from self.message_handler.save(message(123))
        domopyc_server.now = lambda: datetime(2015, 5, 28, 12, 10, 0, tzinfo=timezone.utc)
        yield from self.message_handler.save(message(321))

        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/current_cost')

        json_response = yield from response.json()
        self.assertEqual(2, len(json_response['points']))
        self.assertEqual(123, json_response['points'][0][0])
        self.assertEqual(321, json_response['points'][1][0])



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
        self.pool.close()

    # @async_coro
    # def test_get_current_cost_history_one_line(self):
    #     yield from self.message_handler.save({'date': datetime(2015, 5, 28, 12, 0, 0, tzinfo=timezone.utc), 'watt': 123, 'minutes': 10, 'nb_data': 120, 'temperature': 20.2})
    #
    #     response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/current_cost')
    #     json_response = yield from response.json()
    #
    #     self.assertEqual('2015-05-28T12:00:00', json_response['start'])
    #     self.assertEqual(0, int(json_response['interval']))
    #     self.assertEqual(1, len(json_response['data']))
    #     self.assertEqual(123, json_response['data'][0])

    @async_coro
    def test_get_current_cost_by_day_with_previous_day(self):
        yield from self.message_handler.save({'date': datetime(2015, 5, 29, 12, 10, 0, tzinfo=timezone.utc), 'watt': 1000, 'minutes': 60, 'nb_data': 120, 'temperature': 20.6})
        yield from self.message_handler.save({'date': datetime(2015, 5, 30, 12, 20, 0, tzinfo=timezone.utc), 'watt': 500, 'minutes': 180, 'nb_data': 120, 'temperature': 20.2})

        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/power/day/%s' % int(datetime(2015, 5, 30, 0, 0).timestamp()))
        json_response = yield from response.json()

        self.assertEqual(1, len(json_response['day_data']))
        self.assertEqual(1, len(json_response['previous_day_data']))
        self.assertEqual(['2015-05-30T12:20:00', 500, 20.2], json_response['day_data'][0])
        self.assertEqual(['2015-05-29T12:10:00', 1000, 20.6], json_response['previous_day_data'][0])



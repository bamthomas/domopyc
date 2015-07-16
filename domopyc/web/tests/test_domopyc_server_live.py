import asyncio

import aiohttp
import aiomysql
from domopyc.daq.current_cost_sensor import CURRENT_COST_KEY
import os
from domopyc.test_utils.ut_async import async_coro
from domopyc.test_utils.ut_redis import WithRedis
from domopyc.web import domopyc_server

__author__ = 'bruno'


class GetLiveData(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                            user='test', password='test', db='test',
                                                            loop=asyncio.get_event_loop())
        os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/..')
        self.server = yield from domopyc_server.init(asyncio.get_event_loop(), mysql_pool=self.pool)

    @async_coro
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()
        self.server.close()

    @async_coro
    def test_live_data(self):
        ws = yield from aiohttp.ws_connect('http://localhost:8080/livedata/power')
        yield from self.connection.publish(CURRENT_COST_KEY, 'a message')
        message = yield from asyncio.wait_for(ws.receive(), 2)

        self.assertEqual('a message', message.data)
        yield from ws.close()
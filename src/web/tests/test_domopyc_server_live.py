import asyncio

import aiohttp
from daq.current_cost_sensor import CURRENT_COST_KEY
import os
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis
from web import domopyc_server

__author__ = 'bruno'


class GetLiveData(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/..')
        self.server = yield from domopyc_server.init_frontend(asyncio.get_event_loop())

    @async_coro
    def tearDown(self):
        self.server.close()

    @async_coro
    def test_live_data(self):
        ws = yield from aiohttp.ws_connect('http://localhost:8080/livedata/power')
        yield from self.connection.publish(CURRENT_COST_KEY, 'a message')
        message = yield from asyncio.wait_for(ws.receive(), 2)

        self.assertEqual('a message', message.data)
        yield from ws.close()
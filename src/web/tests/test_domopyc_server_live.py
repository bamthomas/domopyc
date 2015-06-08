from datetime import datetime
from json import loads
import asyncio

import aiohttp
import os
from subscribers import redis_toolbox
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis
from web import domopyc_server

__author__ = 'bruno'


class GetLiveData(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/..')
        self.server = yield from domopyc_server.init(asyncio.get_event_loop())
        yield from self.connection.delete([self.redis_key])

    @async_coro
    def tearDown(self):
        self.server.close()

    @async_coro
    def test_live_data(self):
        yield from self.connection.zadd('current_cost_live_data', {'305': redis_toolbox.now().timestamp()})

        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/data_since/5')

        val = yield from response.read()
        self.assertEqual(loads(val.decode()), {"points": [{'watt': 305}]})

    @property
    def redis_key(self):
        return 'current_cost_%s' % datetime.now().strftime('%Y-%m-%d')

import asyncio
import configparser

import aiohttp
import aiomysql
from domopyc.daq.current_cost_sensor import CURRENT_COST_KEY
from domopyc.test_utils.ut_redis import WithRedis
from domopyc.web import domopyc_server

__author__ = 'bruno'


class GetLiveData(WithRedis):
    @asyncio.coroutine
    def setUp(self):
        yield from super().setUp()
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                            user='test', password='test', db='test',
                                                            loop=asyncio.get_event_loop())
        self.server = yield from domopyc_server.init(asyncio.get_event_loop(), mysql_pool=self.pool, port=12345, config=configparser.ConfigParser())

    @asyncio.coroutine
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()
        self.server.close()

    @asyncio.coroutine
    def test_live_data(self):
        ws = yield from aiohttp.ws_connect('http://localhost:12345/livedata/power')
        yield from self.connection.publish(CURRENT_COST_KEY, 'a message')
        message = yield from asyncio.wait_for(ws.receive(), 2)

        self.assertEqual('a message', message.data)
        yield from ws.close()
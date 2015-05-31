from datetime import datetime, timedelta, timezone
from json import dumps, loads
import asyncio
import aiohttp
import os

from iso8601_json import Iso8601DateEncoder, with_iso8601_date
from subscribers import redis_toolbox
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis
from web import domopyc_server
from web.domopyc_server import get_current_cost_data

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
    def test_get_data_of_current_day(self):
        domopyc_server.now = lambda: datetime.now(tz=timezone.utc)
        expected_json = {'date': domopyc_server.now(), 'watt': 305, 'temperature': 21.4}
        yield from self.connection.lpush(self.redis_key, [dumps(expected_json, cls=Iso8601DateEncoder)])

        data = yield from get_current_cost_data(self.connection)
        self.assertEquals(len(data), 1)
        self.assertEquals(data, [expected_json])

        yield from self.connection.lpush(self.redis_key, [
            dumps({'date': datetime.now() + timedelta(seconds=7), 'watt': 432, 'temperature': 20},
                  cls=Iso8601DateEncoder)])
        self.assertEquals(len((yield from get_current_cost_data(self.connection))), 2)

    @async_coro
    def test_today(self):
        domopyc_server.now = lambda: datetime.now(tz=timezone.utc)
        expected_json = {'date': domopyc_server.now(), 'watt': 305, 'temperature': 21.4}
        yield from self.connection.lpush(self.redis_key, [dumps(expected_json, cls=Iso8601DateEncoder)])

        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/today')

        val = yield from response.read()
        self.assertDictEqual(loads(val.decode(), object_hook=with_iso8601_date), {"points": [expected_json]})

    @async_coro
    def test_live_data(self):
        yield from self.connection.zadd('current_cost_live_data', {'305': redis_toolbox.now().timestamp()})

        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/data_since/5')

        val = yield from response.read()
        self.assertEqual(loads(val.decode()), {"points": [{'watt': 305}]})

    @property
    def redis_key(self):
        return 'current_cost_%s' % datetime.now().strftime('%Y-%m-%d')

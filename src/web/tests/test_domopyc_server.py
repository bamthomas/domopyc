from datetime import datetime, timedelta, timezone
from json import dumps
import asyncio
import os

from iso8601_json import Iso8601DateEncoder
from test_utils.ut_async import async_coro
from test_utils.ut_redis import WithRedis
from web import domopyc_server
from web.domopyc_server import get_current_cost_data


__author__ = 'bruno'


class RedisGetDataOfDay(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/..')
        yield from domopyc_server.init(asyncio.get_event_loop())
        yield from self.connection.delete([self.redis_key])

    @async_coro
    def test_get_data_of_current_day(self):
        domopyc_server.now = lambda: datetime.now(tz=timezone.utc)
        expected_json = {'date': domopyc_server.now(), 'watt': 305, 'temperature': 21.4}
        yield from self.connection.lpush(self.redis_key, [dumps(expected_json, cls=Iso8601DateEncoder)])

        data = yield from get_current_cost_data(self.connection)
        self.assertEquals(len(data), 1)
        self.assertEquals(data, [expected_json])

        yield from self.connection.lpush(self.redis_key,[dumps({'date': datetime.now() + timedelta(seconds=7), 'watt': 432, 'temperature': 20}, cls=Iso8601DateEncoder)])
        self.assertEquals(len((yield from get_current_cost_data(self.connection))), 2)

    @property
    def redis_key(self):
        return 'current_cost_%s' % datetime.now().strftime('%Y-%m-%d')
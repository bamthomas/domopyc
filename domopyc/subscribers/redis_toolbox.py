# coding=utf-8
from datetime import datetime
from statistics import mean
from json import loads, dumps
import logging
import asyncio

from asyncio_redis import ZScoreBoundary
import asyncio_redis
from tzlocal import get_localzone

from domopyc.subscribers.toolbox import AverageMemoryMessageHandler
from domopyc.iso8601_json import with_iso8601_date, Iso8601DateEncoder


CURRENT_COST = 'current_cost'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')


def now(): return datetime.now(tz=get_localzone())

@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class AsyncRedisSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_pool, message_handler, pubsub_key):
        self.pubsub_key = pubsub_key
        self.message_handler = message_handler
        self.redis_pool = redis_pool
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.redis_pool.start_subscribe()
        yield from self.subscriber.subscribe([self.pubsub_key])

    def start(self, for_n_messages=0):
        predicate = AsyncRedisSubscriber.infinite_loop if for_n_messages == 0 \
            else AsyncRedisSubscriber.wait_value(for_n_messages)
        self.message_loop_task = asyncio.async(self.message_loop(predicate))
        return self

    @asyncio.coroutine
    def message_loop(self, predicate):
        i = 0
        while predicate(i):
            try:
                i += 1
                message_str = yield from self.subscriber.next_published()
                message = loads(message_str.value, object_hook=with_iso8601_date)
                yield from self.message_handler.handle(message)
            except Exception as e:
                LOGGER.exception(e)



class RedisAverageMessageHandler(AverageMemoryMessageHandler):
    def __init__(self, db, keys, average_period_minutes=0):
        super(RedisAverageMessageHandler, self).__init__(keys, average_period_minutes)
        self.redis_conn = db

    @asyncio.coroutine
    def save(self, average_message):
        key = 'current_cost_%s' % average_message['date'].strftime('%Y-%m-%d')
        lpush_return = yield from self.redis_conn.lpush(key, [dumps(average_message, cls=Iso8601DateEncoder)])
        if lpush_return == 1:
            yield from self.redis_conn.expire(key, 5 * 24 * 3600)


class RedisTimeCappedSubscriber(AsyncRedisSubscriber):
    def __init__(self, redis_pool, indicator_name, max_data_age_in_seconds=0,
                 pubsub_key="rfxcom",
                 indicator_key='temperature'):
        super().__init__(redis_pool, self, pubsub_key)
        self.indicator_key = indicator_key
        self.max_data_age_in_seconds = max_data_age_in_seconds
        self.indicator_name = indicator_name

    @asyncio.coroutine
    def handle(self, message):
        yield from self.redis_pool.zadd(self.indicator_name,
                                        {dumps({'date': message['date'], self.indicator_key: message[self.indicator_key]}, cls=Iso8601DateEncoder): message['date'].timestamp()})
        if self.max_data_age_in_seconds:
            yield from self.redis_pool.zremrangebyscore(self.indicator_name, ZScoreBoundary('-inf'),
                                                        ZScoreBoundary(
                                                            now().timestamp() - self.max_data_age_in_seconds))

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.redis_pool.zrange(self.indicator_name, 0, -1)
        d = yield from val.asdict()
        return mean((float(loads(v, object_hook=with_iso8601_date)[self.indicator_key]) for v in list(d))) if d else 0.0

    @asyncio.coroutine
    def get_data(self, since_seconds=60):
        t = yield from self.redis_pool.zrangebyscore(self.indicator_name,
                                                            ZScoreBoundary(now().timestamp() - since_seconds),
                                                            ZScoreBoundary(now().timestamp()))
        data_set = yield from t.asdict()
        return list(map(lambda value: loads(value, object_hook=with_iso8601_date), list(data_set)))


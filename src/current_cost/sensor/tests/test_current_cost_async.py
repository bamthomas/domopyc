from asyncio import Queue
import asyncio
import functools
from json import dumps, loads
import unittest
from datetime import datetime, timezone

import asyncio_redis
from current_cost.iso8601_json import Iso8601DateEncoder, with_iso8601_date


__author__ = 'bruno'



@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


def async_coro(f):
    def wrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            coro = asyncio.coroutine(f)
            future = coro(*args, **kwargs)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)
        return wrapper
    return wrap(f)


class WithRedis(unittest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.connection = yield from create_redis_pool()
        yield from self.connection.flushdb()

    @asyncio.coroutine
    def tearDown(self):
        self.connection.close()


class AsyncRedisSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_conn, message_handler, pubsub_key):
        self.pubsub_key = pubsub_key
        self.message_handler = message_handler
        self.redis_conn = redis_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.redis_conn.start_subscribe()
        yield from self.subscriber.subscribe([self.pubsub_key])

    def start(self, for_n_messages=0):
        predicate = AsyncRedisSubscriber.infinite_loop if for_n_messages == 0 else AsyncRedisSubscriber.wait_value(for_n_messages)
        self.message_loop_task = asyncio.async(self.message_loop(predicate))
        return self

    @asyncio.coroutine
    def message_loop(self, predicate):
        i = 0
        while predicate(i):
            i += 1
            message_str = yield from self.subscriber.next_published()
            message = loads(message_str.value, object_hook=with_iso8601_date)
            yield from self.message_handler.handle(message)


class RedisSubscribeLoopTest(WithRedis):
    @async_coro
    def setUp(self):
        yield from super().setUp()
        class TestMessageHandler(object):
            queue = Queue()
            @asyncio.coroutine
            def handle(self, message):
                yield from self.queue.put(message)
        self.message_handler = TestMessageHandler()
        self.subscriber = AsyncRedisSubscriber(self.connection, self.message_handler, 'key')

    @async_coro
    def test_subscribe_loop(self):
        self.subscriber.start(1)
        expected = {'date': datetime.now(timezone.utc), 'watt': '123'}

        yield from self.connection.publish('key', dumps(expected, cls=Iso8601DateEncoder))

        event = yield from asyncio.wait_for(self.message_handler.queue.get(), 2)
        self.assertDictEqual(event, expected)


# coding=utf-8
import asyncio
import unittest

import asyncio_redis
import asynctest


@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class WithRedis(asynctest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.connection = yield from create_redis_pool()
        yield from self.connection.flushdb()

    def tearDown(self):
        self.connection.close()

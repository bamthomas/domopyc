# coding=utf-8
from unittest import TestCase
import aiohttp
import asyncio
from test_utils.ut_async import async_coro
from web import aio_domopyc_server


class TestFumee(TestCase):
    @async_coro
    def setUp(self):
        yield from aio_domopyc_server.init(asyncio.get_event_loop())

    @async_coro
    def test_fumee(self):
        response = yield from aiohttp.request('GET', 'http://127.0.0.1:8080/url')
        val = yield from response.read()
        self.assertEqual(val, b'hello world')

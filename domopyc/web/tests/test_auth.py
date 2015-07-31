import asyncio
import aiohttp
import aiomysql
from asynctest.case import TestCase
from domopyc.web import domopyc_server


class TestAuth(TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        self.server = yield from domopyc_server.init(self.loop, self.pool, port=12345)
        self.session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('foo', 'bar'), loop=self.loop)

    @asyncio.coroutine
    def tearDown(self):
        self.session.close()
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_auth_page(self):
        resp = yield from aiohttp.request('GET', 'http://127.0.0.1:12345/auth')
        body = yield from resp.text()

        self.assertEqual(200, resp.status)
        self.assertTrue('login' in body)
        self.assertTrue('password' in body)
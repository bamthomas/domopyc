import asyncio
import configparser

import aiohttp
import aiomysql
from asynctest.case import TestCase
from domopyc.web import domopyc_server
import hashlib


class TestAuth(TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=asyncio.get_event_loop())

        config = configparser.ConfigParser()
        config['users'] = {'foo': hashlib.sha224('pass'.encode()).hexdigest()}
        config['domopyc'] = {'title' : 'title'}

        self.server = yield from domopyc_server.init(self.loop, self.pool, port=12345, config=config)

    @asyncio.coroutine
    def tearDown(self):
        self.server.close()
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_get_page_without_userconfig(self):
        config = configparser.ConfigParser()
        config['domopyc'] = {'title' : 'title'}
        server_without_user_config = yield from domopyc_server.init(self.loop, self.pool, port=12346, config=config)
        resp = yield from aiohttp.request('GET', 'http://127.0.0.1:12346/menu/apropos', allow_redirects=False)

        self.assertEqual(200, resp.status)
        server_without_user_config.close()

    @asyncio.coroutine
    def test_get_page_without_auth(self):
        resp = yield from aiohttp.request('GET', 'http://127.0.0.1:12345/menu/apropos', allow_redirects=False)

        self.assertEqual(401, resp.status)
        self.assertEqual(resp.headers['WWW-Authenticate'], 'Basic realm="domopyc"')

    @asyncio.coroutine
    def test_get_page_with_unknown_user(self):
        session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('bar', 'unused'), loop=self.loop)
        resp = yield from session.get('http://127.0.0.1:12345/menu/apropos')

        self.assertEqual(401, resp.status)

    @asyncio.coroutine
    def test_get_page_with_bad_password(self):
        session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('foo', 'badpass'), loop=self.loop)
        resp = yield from session.get('http://127.0.0.1:12345/menu/apropos')

        self.assertEqual(401, resp.status)

    @asyncio.coroutine
    def test_get_page_with_auth(self):
        session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('foo', 'pass'), loop=self.loop)
        resp = yield from session.get('http://127.0.0.1:12345/menu/apropos')

        self.assertEqual(200, resp.status)
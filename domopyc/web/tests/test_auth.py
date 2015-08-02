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

        self.server = yield from domopyc_server.init(self.loop, self.pool, port=12345, config=config)
        self.session = aiohttp.ClientSession(auth=aiohttp.BasicAuth('foo', 'pass'), loop=self.loop)

    @asyncio.coroutine
    def tearDown(self):
        self.session.close()
        self.server.close()
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_auth_page(self):
        resp = yield from aiohttp.request('GET', 'http://127.0.0.1:12345/auth')
        body = yield from resp.text()

        self.assertEqual(200, resp.status)
        self.assertTrue('login' in body)
        self.assertTrue('password' in body)

    @asyncio.coroutine
    def test_login_unknown_user(self):
        resp = yield from aiohttp.request('POST', 'http://127.0.0.1:12345/login', data={'login': 'bar', 'password': 'unused'})

        self.assertEqual(200, resp.status)
        body = yield from resp.text()

        self.assertTrue('login' in body)
        self.assertTrue('password' in body)
        self.assertTrue('identifiant ou mot de passe incorrect' in body)

    @asyncio.coroutine
    def test_login_fail(self):
        resp = yield from aiohttp.request('POST', 'http://127.0.0.1:12345/login', data={'login': 'foo', 'password': 'bad_pass'})

        self.assertEqual(200, resp.status)
        body = yield from resp.text()

        self.assertTrue('identifiant ou mot de passe incorrect' in body)

    @asyncio.coroutine
    def test_login_success(self):
        resp = yield from aiohttp.request('POST', 'http://127.0.0.1:12345/login', data={'login': 'foo', 'password': 'pass'})

        self.assertEqual(200, resp.status)
        body = yield from resp.text()

        self.assertTrue('Consommation électrique' in body)

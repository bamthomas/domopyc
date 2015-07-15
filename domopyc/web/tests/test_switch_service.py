# coding=utf-8
import asyncio

import aiomysql
import asynctest
from domopyc.web.switch_service import SwichService


class SwitchServiceTest(asynctest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=self.loop)
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("drop table if EXISTS domopyc_switch")
            yield from cur.close()

            self.switch_service = SwichService(self.pool)

    @asyncio.coroutine
    def tearDown(self):
        self.pool.close()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_get_all_no_data(self):
        self.assertEqual({'switches': []}, (yield from self.switch_service.get_all()))

    @asyncio.coroutine
    def test_insert_and_delete_new_switch(self):
        yield from self.switch_service.insert('1234567', 'my new switch')

        switches = yield from self.switch_service.get_all()
        self.assertEqual({'switches': [{'id': '1234567', 'label': 'my new switch', 'state': 0}]}, switches)

        yield from self.switch_service.delete('1234567')
        self.assertEqual({'switches': []}, (yield from self.switch_service.get_all()))

    @asyncio.coroutine
    def test_switch_on_off(self):
        yield from self.switch_service.insert('1234567', 'my new switch')

        yield from self.switch_service.switch('1234567', '1')

        switches = yield from self.switch_service.get_all()
        self.assertEqual({'switches': [{'id': '1234567', 'label': 'my new switch', 'state': 1}]}, switches)

    @asyncio.coroutine
    def test_insert_new_switch_bad_id(self):
        with self.assertRaises(ValueError):
            yield from self.switch_service.insert('123456', 'too short switch id')
        with self.assertRaises(ValueError):
            yield from self.switch_service.insert('12345678', 'too long switch id')
        with self.assertRaises(ValueError):
            yield from self.switch_service.insert('ABCDEFG', 'G is not hexadecimal')
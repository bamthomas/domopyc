import asyncio
import aiomysql
import asynctest
from domopyc.web.keep_alive_service import KeepAliveService


class KeepAliveServiceTest(asynctest.TestCase):
    @asyncio.coroutine
    def setUp(self):
        self.root_conn = yield from aiomysql.connect(host='127.0.0.1', port=3306,
                                                            user='root', password='test', db='test',
                                                            loop=self.loop)
        cur = yield from self.root_conn.cursor()
        yield from cur.execute("SET GLOBAL wait_timeout=1")
        yield from cur.close()

        self.pool = yield from aiomysql.create_pool(minsize=2, host='127.0.0.1', port=3306,
                                                    user='test', password='test', db='test',
                                                    loop=self.loop)

        self.keep_alive = KeepAliveService(self.pool, self.loop, 1).start()

    @asyncio.coroutine
    def tearDown(self):
        cur = yield from self.root_conn.cursor()
        yield from cur.execute("SET GLOBAL wait_timeout=28800")
        yield from cur.close()
        yield from self.root_conn.ensure_closed()

        self.pool.close()
        self.keep_alive.stop()
        yield from self.pool.wait_closed()

    @asyncio.coroutine
    def test_timeout(self):
        yield from self.keep_alive.keep_alive_request()

        yield from asyncio.sleep(3)

        self.assertEqual((1, ), (yield from self.keep_alive.keep_alive_request()))

import asyncio


class KeepAliveService(object):
    def __init__(self, pool, loop=asyncio.get_event_loop(), mysql_wait_timeout=28800):
        self.keep_alive_interval = mysql_wait_timeout / (pool._minsize * 2)
        self.loop = loop
        self.pool = pool
        self.next_handler = None

    def start(self):
        self.keep_alive()
        return self

    def keep_alive(self):
        self.next_handler = self.loop.call_later(self.keep_alive_interval, self.keep_alive)
        asyncio.async(self.keep_alive_request())

    @asyncio.coroutine
    def keep_alive_request(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute('SELECT 1')
            one = yield from cur.fetchall()
            yield from cur.close()
            return one[0]

    def stop(self):
        if self.next_handler:
            self.next_handler.cancel()

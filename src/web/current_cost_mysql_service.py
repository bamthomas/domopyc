# coding=utf-8
import asyncio


class CurrentCostDatabaseReader(object):
    def __init__(self, pool):
        self.pool = pool

    @asyncio.coroutine
    def get_current_cost_data(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT watt from current_cost")
            result =yield from cur.fetchall()
            yield from cur.close()
            return result
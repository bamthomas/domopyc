# coding=utf-8
import asyncio
from datetime import datetime


class CurrentCostDatabaseReader(object):
    def __init__(self, pool):
        self.pool = pool

    @asyncio.coroutine
    def get_current_cost_data(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            # yield from cur.execute("SELECT timestamp, watt from current_cost order by timestamp ")
            yield from cur.execute("select timestamp(date(timestamp), MAKETIME(0,0,0)) as day, sum((watt * minutes)/60)/1000 from current_cost group by date(timestamp) order by day ")
            result = yield from cur.fetchall()
            yield from cur.close()
            return result


# coding=utf-8
import asyncio


class CurrentCostDatabaseReader(object):
    def __init__(self, pool):
        self.pool = pool

    @asyncio.coroutine
    def get_current_cost_data(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT timestamp, watt from current_cost order by timestamp ")
            result = yield from cur.fetchall()
            yield from cur.close()
            return get_start_date(result), get_intervall(result), remove_timestamp(result)


def get_start_date(lst):
    return lst[0][0]

def get_intervall(lst):
    if len(lst) == 0 or len(lst) == 1:
        return 0
    older = get_start_date(lst)
    newer = lst[-1][0]
    delta = newer - older
    return delta.total_seconds() * 1000 / (len(lst) - 1)

def remove_timestamp(lst):
    return [val for [_, val] in lst]

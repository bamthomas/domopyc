# coding=utf-8
import asyncio
from datetime import datetime, timedelta, time
from decimal import Decimal


class CurrentCostDatabaseReader(object):
    def __init__(self, pool, full_hours_start=time(0, 0), full_hours_stop=time(23, 59, 59)):
        self.full_hours_stop = full_hours_stop
        self.full_hours_start = full_hours_start
        self.pool = pool

    @asyncio.coroutine
    def get_history(self):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT timestamp(date(timestamp), MAKETIME(0,0,0)) AS day, "
                                   "round(sum(watt * minutes)) / (60 * 1000) FROM current_cost "
                                   "GROUP BY date(timestamp) ORDER BY day ")
            result = yield from cur.fetchall()
            yield from cur.close()
            return result

    @asyncio.coroutine
    def get_by_day(self, date_time):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT timestamp, watt, temperature from current_cost where timestamp >= %s "
                                   "and timestamp < %s ORDER BY TIMESTAMP ", (date_time, date_time + timedelta(days=1)))
            result = yield from cur.fetchall()
            yield from cur.close()
            return result

    @asyncio.coroutine
    def get_costs(self, since):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT timestamp(date(timestamp), MAKETIME(0,0,0)) AS day, "
                                   "sum(watt * minutes) / (60 * 1000) FROM current_cost "
                                   "WHERE timestamp >= %s AND TIME(timestamp) >= %s and TIME(timestamp) <= %s "
                                   "GROUP BY date(timestamp) ORDER BY day ", (since, self.full_hours_start, self.full_hours_stop ))
            full = yield from cur.fetchall()
            yield from cur.execute("SELECT timestamp(date(timestamp), MAKETIME(0,0,0)) AS day, "
                                   "sum(watt * minutes) / (60 * 1000) FROM current_cost "
                                   "WHERE timestamp >= %s AND (TIME(timestamp) < %s OR TIME(timestamp) > %s) "
                                   "GROUP BY date(timestamp) ORDER BY day ", (since, self.full_hours_start, self.full_hours_stop))
            empty = yield from cur.fetchall()
            yield from cur.close()
            return merge_full_and_empty_hours(full, empty)


def merge_full_and_empty_hours(full, empty):
    print(full)
    print(empty)

    full_hours_dict = dict(full)
    empty_hours_dict = dict(empty)

    merged_dict_from_full = {k: (v, empty_hours_dict.get(k, Decimal(0))) for (k, v) in full_hours_dict.items()}
    merged_dict_from_empty = {k: (full_hours_dict.get(k, Decimal(0)), v) for (k, v) in empty_hours_dict.items()}
    merged_dict_from_full.update(merged_dict_from_empty)
    return tuple(sorted(merged_dict_from_full.items()))

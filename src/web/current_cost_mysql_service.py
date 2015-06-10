# coding=utf-8
import asyncio
from datetime import datetime, timedelta, time
from decimal import Decimal
from tzlocal import get_localzone


def now():
    return datetime.now(tz=get_localzone())


def get_sql_period_function(since):
    if now() - since > timedelta(weeks=11):
        return 'MONTH'
    if now() - since >= timedelta(days=15):
        return 'WEEK'
    if now() - since < timedelta(days=15):
        return 'DAYOFYEAR'


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
        period_func = get_sql_period_function(since)
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT timestamp(date(timestamp), MAKETIME(0,0,0)) AS day, "
                                   "sum(watt * minutes) / (60 * 1000), {period_func}(timestamp) as period FROM current_cost "
                                   "WHERE timestamp >= %s AND TIME(timestamp) >= %s and TIME(timestamp) <= %s "
                                   "GROUP BY period ORDER BY day ".format(period_func=period_func), (since, self.full_hours_start, self.full_hours_stop))
            full = yield from cur.fetchall()
            yield from cur.execute("SELECT timestamp(date(timestamp), MAKETIME(0,0,0)) AS day, "
                                   "sum(watt * minutes) / (60 * 1000), {period_func}(timestamp) as period FROM current_cost "
                                   "WHERE timestamp >= %s AND (TIME(timestamp) < %s OR TIME(timestamp) > %s) "
                                   "GROUP BY period ORDER BY day ".format(period_func=period_func), (since, self.full_hours_start, self.full_hours_stop))
            empty = yield from cur.fetchall()
            yield from cur.close()

            def keep_two_first_fields(iterable):
                return map(lambda t: t[0:2], iterable)
            return merge_full_and_empty_hours(keep_two_first_fields(full), keep_two_first_fields(empty))

    @asyncio.coroutine
    def get_last_value(self, table, field):
        with (yield from self.pool) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("SELECT {field} from {table} order by timestamp LIMIT 1".format(field=field, table=table))
            value = yield from cur.fetchone()
            yield from cur.close()
            return float(value[0])


def merge_full_and_empty_hours(full, empty):
    full_hours_dict = dict(full)
    empty_hours_dict = dict(empty)

    merged_dict_from_full = {k: (v, empty_hours_dict.get(k, Decimal(0))) for (k, v) in full_hours_dict.items()}
    merged_dict_from_empty = {k: (full_hours_dict.get(k, Decimal(0)), v) for (k, v) in empty_hours_dict.items()}
    merged_dict_from_full.update(merged_dict_from_empty)
    return tuple(sorted(merged_dict_from_full.items()))

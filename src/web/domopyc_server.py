# coding=utf-8
import asyncio
from datetime import datetime, timedelta, time
from json import dumps
import logging
import aiohttp

from aiohttp import web
import aiohttp_jinja2
import aiomysql
import asyncio_redis
from daq.rfxcom_emiter_receiver import RFXCOM_KEY
from iso8601 import iso8601
import jinja2
from daq.current_cost_sensor import CURRENT_COST_KEY
from iso8601_json import Iso8601DateEncoder
from tzlocal import get_localzone
from web.current_cost_mysql_service import CurrentCostDatabaseReader

now = datetime.now
root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)
logger = logging.getLogger('domopyc_server')

@asyncio.coroutine
def create_redis_pool(nb_conn):
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=nb_conn)
    return connection

@asyncio.coroutine
def create_mysql_pool():
    pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                               user='test', password='test', db='test',
                                               loop=asyncio.get_event_loop())
    return pool


@asyncio.coroutine
def stream(request):
    redis_pool = yield from create_redis_pool(1)
    subscriber = yield from redis_pool.start_subscribe()
    yield from subscriber.subscribe([CURRENT_COST_KEY])
    ws = web.WebSocketResponse()
    ws.start(request)
    continue_loop = True
    while continue_loop:
        reply = yield from subscriber.next_published()
        if ws.closed:
            logger.info('leaving web socket stream, usubscribing')
            yield from subscriber.unsubscribe()
            continue_loop = False
        else:
            ws.send_str(reply.value)

    return ws


@aiohttp_jinja2.template('index.j2')
def home(_):
    return {}


@asyncio.coroutine
def menu_item(request):
    page = request.match_info['page']
    return aiohttp_jinja2.render_template('%s.j2' % page, request, {})


@asyncio.coroutine
def power_history(request):
    data = yield from request.app['current_cost_service'].get_history()
    return web.Response(body=dumps({'data': data}, cls=Iso8601DateEncoder).encode(),
                        headers={'Content-Type': 'application/json'})

@asyncio.coroutine
def power_by_day(request):
    iso_date = iso8601.parse_date(request.match_info['iso_date'], default_timezone=get_localzone())
    data = yield from request.app['current_cost_service'].get_by_day(iso_date)
    previous_data = yield from request.app['current_cost_service'].get_by_day(iso_date - timedelta(days=1))
    return web.Response(body=dumps({'day_data': data, 'previous_day_data': previous_data}, cls=Iso8601DateEncoder).encode(),
                        headers={'Content-Type': 'application/json'})

@asyncio.coroutine
def power_costs(request):
    since = iso8601.parse_date(request.match_info['since'], default_timezone=get_localzone())
    data = yield from request.app['current_cost_service'].get_costs(since)
    return web.Response(body=dumps({'data': data}, cls=Iso8601DateEncoder).encode(),
                        headers={'Content-Type': 'application/json'})


@asyncio.coroutine
def init(aio_loop, mysql_pool=None):
    mysql_pool_local = mysql_pool if mysql_pool is not None else (yield from create_mysql_pool())
    app = web.Application(loop=aio_loop)
    app['current_cost_service'] = CurrentCostDatabaseReader(mysql_pool_local, full_hours_start=time(7), full_hours_stop=time(23))

    app.router.add_static(prefix='/static', path='static')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

    app.router.add_route('GET', '/livedata/power', stream)
    app.router.add_route('GET', '/', home)
    app.router.add_route('GET', '/menu/{page}', menu_item)
    app.router.add_route('GET', '/power/history', power_history)
    app.router.add_route('GET', '/power/day/{iso_date}', power_by_day)
    app.router.add_route('GET', '/power/costs/{since}', power_costs)

    srv = yield from aio_loop.create_server(app.make_handler(), '127.0.0.1', 8080)
    print("Server started at http://127.0.0.1:8080")
    return srv


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()

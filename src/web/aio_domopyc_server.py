# coding=utf-8
import asyncio
from datetime import datetime
from json import loads

from aiohttp import web
import aiohttp_jinja2
import asyncio_redis
import jinja2

from daq.current_cost_sensor import CURRENT_COST_KEY
from iso8601_json import with_iso8601_date
from subscribers.redis_toolbox import RedisTimeCappedSubscriber


now = datetime.now


@asyncio.coroutine
def create_redis_connection():
    connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)
    return connection


@asyncio.coroutine
def message_stream():
    redis_conn = yield from create_redis_connection()
    subscriber = yield from redis_conn.start_subscribe()
    yield from subscriber.subscribe([CURRENT_COST_KEY])
    while True:
        reply = yield from subscriber.next_published()
        return 'data: %s\n\n' % loads(reply.value, object_hook=with_iso8601_date)


@asyncio.coroutine
def stream(request):
    ws = web.WebSocketResponse()
    ws.start(request)
    while True:
        data = yield from message_stream()
        ws.send_str(data)
    return ws


@aiohttp_jinja2.template('index.html')
def home(_):
    return {}

@aiohttp_jinja2.template('apropos.html')
def apropos(_):
    return {}
@aiohttp_jinja2.template('commandes.html')
def commandes(_):
    return {}
@aiohttp_jinja2.template('conso_electrique.html')
def conso_electrique(_):
    return {}
@aiohttp_jinja2.template('conso_temps_reel.html')
def conso_temps_reel(_):
    return {}
@aiohttp_jinja2.template('piscine.html')
def piscine(_):
    return {}

@asyncio.coroutine
def today():
    return {'points': (yield from get_current_cost_data())}

@asyncio.coroutine
def setup_redis_connection():
    redis_conn = yield from create_redis_connection()

@asyncio.coroutine
def setup_live_data_subscriber():
    redis_conn = yield from create_redis_connection()
    RedisTimeCappedSubscriber(redis_conn, 'current_cost_live_data', 3600, pubsub_key=CURRENT_COST_KEY, indicator_key='watt').start()

@asyncio.coroutine
def livedata(request):
    seconds = request.match_info['seconds']
    return {'points': []}

@asyncio.coroutine
def get_current_cost_data():
    return []
#     list_reply = yield from app.config['redis_connection'].lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1)
#     l = yield from list_reply.aslist()
#     return list(map(lambda json: loads(json, object_hook=with_iso8601_date), l))


@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_static(prefix='/static', path='static')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

    app.router.add_route('GET', '/stream', stream)
    app.router.add_route('GET', '/', home)
    app.router.add_route('GET', '/today', today)
    app.router.add_route('GET', '/data_since/{seconds}', livedata)
    app.router.add_route('GET', '/menu/apropos', apropos)
    app.router.add_route('GET', '/menu/piscine', piscine)
    app.router.add_route('GET', '/menu/commandes', commandes)
    app.router.add_route('GET', '/menu/conso_electrique', conso_electrique)
    app.router.add_route('GET', '/menu/conso_temps_reel', conso_temps_reel)


    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 8080)
    print("Server started at http://127.0.0.1:8080")
    return srv


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
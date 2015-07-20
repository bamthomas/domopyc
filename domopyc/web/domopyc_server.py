# coding=utf-8
import asyncio
from datetime import datetime, timedelta, time
from json import dumps
import logging
import os

import aiohttp_jinja2

import asyncio_redis
from iso8601 import iso8601
from tzlocal import get_localzone

from aiohttp import web
from aiohttp.web_ws import WebSocketResponse
import aiomysql
from domopyc.daq.publishers.redis_publisher import RedisPublisher
from domopyc.daq.rfxcom_emiter_receiver import RFXCOM_KEY, RFXCOM_KEY_CMD, create_rfxtrx433e
import jinja2
from domopyc.daq.current_cost_sensor import CURRENT_COST_KEY
from domopyc.indicators.filtration_duration import calculate_in_minutes
from domopyc.iso8601_json import Iso8601DateEncoder
from domopyc.subscribers.mysql_toolbox import MysqlTemperatureMessageHandler
from domopyc.subscribers.redis_toolbox import AsyncRedisSubscriber
from domopyc.web.configuration import PARAMETERS
from domopyc.web.current_cost_mysql_service import CurrentCostDatabaseReader
from domopyc.web.switch_service import SwichService

now = datetime.now
root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)
logger = logging.getLogger('domopyc_server')

TITLE_AND_CONFIG = {'title': PARAMETERS['title'], 'configuration': PARAMETERS}

@asyncio.coroutine
def create_redis_pool(nb_conn=1):
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=nb_conn)
    return connection

@asyncio.coroutine
def create_mysql_pool():
    pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
                                               user='domopyc', password='blah', db='domopyc',
                                               loop=asyncio.get_event_loop())
    return pool

@asyncio.coroutine
def stream(request):
    redis_pool = yield from create_redis_pool(1)
    subscriber = yield from redis_pool.start_subscribe()
    yield from subscriber.subscribe([CURRENT_COST_KEY])
    ws = WebSocketResponse()
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
    return TITLE_AND_CONFIG

@aiohttp_jinja2.template('piscine.j2')
def piscine(request):
    value = yield from request.app['current_cost_service'].get_last_value('pool_temperature', 'temperature')
    return dict(temperature=value, temps_filtrage=str(timedelta(minutes=calculate_in_minutes(value))), **TITLE_AND_CONFIG)

@aiohttp_jinja2.template('apropos.j2')
def apropos(_):
    return TITLE_AND_CONFIG

@aiohttp_jinja2.template('conso_electrique.j2')
def conso_electrique(_):
    return TITLE_AND_CONFIG

@aiohttp_jinja2.template('conso_temps_reel.j2')
def conso_temps_reel(_):
    return TITLE_AND_CONFIG

@aiohttp_jinja2.template('commandes.j2')
def commandes(request):
    switches = yield from request.app['switch_service'].get_all()
    return dict(switches, **TITLE_AND_CONFIG)

@aiohttp_jinja2.template('commandes.j2')
def commandes_add(request):
    parameters = yield from request.post()
    try:
        yield from request.app['switch_service'].insert(parameters["id"], parameters["label"])
    except ValueError as e:
        logger.exception(e)
    switches = yield from request.app['switch_service'].get_all()
    return dict(switches, **TITLE_AND_CONFIG)

@aiohttp_jinja2.template('commandes.j2')
def command_execute(request):
    value = request.match_info['value']
    code_device = request.match_info['code_device']
    yield from request.app['redis_cmd_publisher'].publish({"code_device": code_device, "value": value})
    yield from request.app['switch_service'].switch(code_device, value)
    return TITLE_AND_CONFIG

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
def init(aio_loop, mysql_pool=None, port=8080):
    mysql_pool_local = mysql_pool if mysql_pool is not None else (yield from create_mysql_pool())
    app = web.Application(loop=aio_loop)
    app['current_cost_service'] = CurrentCostDatabaseReader(mysql_pool_local, full_hours_start=time(7), full_hours_stop=time(23))
    app['redis_cmd_publisher'] = RedisPublisher((yield from create_redis_pool()), RFXCOM_KEY_CMD)
    app['switch_service'] = SwichService(mysql_pool_local)

    app.router.add_static(prefix='/static', path=os.path.dirname(__file__) + '/static')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + '/templates'))

    app.router.add_route('GET', '/livedata/power', stream)
    app.router.add_route('GET', '/', home)
    app.router.add_route('GET', '/menu/piscine', piscine)
    app.router.add_route('GET', '/menu/apropos', apropos)
    app.router.add_route('GET', '/menu/conso_electrique', conso_electrique)
    app.router.add_route('GET', '/menu/conso_temps_reel', conso_temps_reel)
    app.router.add_route('GET', '/menu/commandes', commandes)
    app.router.add_route('GET', '/menu/commandes/execute/{code_device}/{value}', command_execute)
    app.router.add_route('POST', '/menu/commandes/add', commandes_add)
    app.router.add_route('GET', '/power/history', power_history)
    app.router.add_route('GET', '/power/day/{iso_date}', power_by_day)
    app.router.add_route('GET', '/power/costs/{since}', power_costs)

    listening_ip = '0.0.0.0'
    srv = yield from aio_loop.create_server(app.make_handler(), listening_ip, port)
    logger.info("Domopyc web server started at http://%s:%s" % (listening_ip, port))
    return srv

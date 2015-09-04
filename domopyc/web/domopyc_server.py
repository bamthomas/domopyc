# coding=utf-8
import asyncio
from datetime import datetime, timedelta, time
from json import dumps
import logging

import aiohttp_jinja2
import asyncio_redis
from iso8601 import iso8601
from tzlocal import get_localzone

import base64
import hashlib
import os
from aiohttp import web
from aiohttp.web_ws import WebSocketResponse
import aiomysql
from domopyc.daq.publishers.redis_publisher import RedisPublisher
from domopyc.daq.rfxcom_emiter_receiver import RFXCOM_KEY_CMD
import jinja2
from domopyc.daq.current_cost_sensor import CURRENT_COST_KEY
from domopyc.indicators.filtration_duration import calculate_in_minutes
from domopyc.iso8601_json import Iso8601DateEncoder
from domopyc.web.current_cost_mysql_service import CurrentCostDatabaseReader
from domopyc.web.switch_service import SwichService

now = datetime.now
root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)
logger = logging.getLogger('domopyc_server')


def get_default_model(config):
    return {'title': config['domopyc']['title'], 'configuration': dict(config['domopyc'])}

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
    return web.HTTPFound('/menu/conso_electrique')

@aiohttp_jinja2.template('piscine.j2')
def piscine(request):
    values = yield from request.app['current_cost_service'].get_values('pool_temperature', 'temperature')
    last_value = values[-1]['temperature']
    return dict(temperature=last_value, temps_filtrage=str(timedelta(minutes=calculate_in_minutes(last_value))), values=values, **get_default_model(request.app['config']))

@aiohttp_jinja2.template('apropos.j2')
def apropos(request):
    return get_default_model(request.app['config'])

@aiohttp_jinja2.template('conso_electrique.j2')
def conso_electrique(request):
    return get_default_model(request.app['config'])

@aiohttp_jinja2.template('commandes.j2')
def commandes(request):
    switches = yield from request.app['switch_service'].get_all()
    return dict(switches, **get_default_model(request.app['config']))

@aiohttp_jinja2.template('commandes.j2')
def commandes_add(request):
    parameters = yield from request.post()
    try:
        yield from request.app['switch_service'].insert(parameters["id"], parameters["label"])
    except ValueError as e:
        logger.exception(e)
    switches = yield from request.app['switch_service'].get_all()
    return dict(switches, **get_default_model(request.app['config']))

@aiohttp_jinja2.template('commandes.j2')
def command_execute(request):
    value = request.match_info['value']
    code_device = request.match_info['code_device']
    yield from request.app['redis_cmd_publisher'].publish({"code_device": code_device, "value": value})
    yield from request.app['switch_service'].switch(code_device, value)
    return get_default_model(request.app['config'])

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
def authentication_middleware(app, handler):
    @asyncio.coroutine
    def basic_auth(request):
        if 'config' not in app is None or 'users' not in app['config']:
            return (yield from handler(request))
        if request.headers.get('AUTHORIZATION') is not None:
            user_pass = base64.b64decode(request.headers.get('AUTHORIZATION').replace('Basic', '').strip()).decode('utf-8')
            login, password = tuple(user_pass.split(':'))
            if login in app['config']['users'] and app['config']['users'][login] == hashlib.sha224(password.encode()).hexdigest():
                return (yield from handler(request))
        return web.HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic realm="domopyc"'})
    return basic_auth

@asyncio.coroutine
def init(aio_loop, mysql_pool, port=8080, config=None, sslcontext=None):
    app = web.Application(loop=aio_loop, middlewares=[authentication_middleware])
    app['current_cost_service'] = CurrentCostDatabaseReader(mysql_pool, full_hours_start=time(7), full_hours_stop=time(23))
    app['redis_cmd_publisher'] = RedisPublisher((yield from create_redis_pool()), RFXCOM_KEY_CMD)
    app['switch_service'] = SwichService(mysql_pool)
    app['config'] = config

    app.router.add_static(prefix='/static', path=os.path.dirname(__file__) + '/static')
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + '/templates'))

    app.router.add_route('GET', '/livedata/power', stream)
    app.router.add_route('GET', '/', home)
    app.router.add_route('GET', '/menu/piscine', piscine)
    app.router.add_route('GET', '/menu/apropos', apropos)
    app.router.add_route('GET', '/menu/conso_electrique', conso_electrique)
    app.router.add_route('GET', '/menu/commandes', commandes)
    app.router.add_route('GET', '/menu/commandes/execute/{code_device}/{value}', command_execute)
    app.router.add_route('POST', '/menu/commandes/add', commandes_add)
    app.router.add_route('GET', '/power/history', power_history)
    app.router.add_route('GET', '/power/day/{iso_date}', power_by_day)
    app.router.add_route('GET', '/power/costs/{since}', power_costs)

    listening_ip = '0.0.0.0'
    srv = yield from aio_loop.create_server(app.make_handler(), listening_ip, port, ssl=sslcontext)
    logger.info("Domopyc web server started at http://%s:%s" % (listening_ip, port))
    return srv

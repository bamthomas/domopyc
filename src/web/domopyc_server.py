from datetime import datetime
from json import loads
import asyncio
import asyncio_redis
from daq.current_cost_sensor import CURRENT_COST_KEY
import flask
from flask.templating import render_template
from iso8601_json import with_iso8601_date
from subscribers.redis_toolbox import RedisTimeCappedSubscriber

__author__ = 'bruno'

app = flask.Flask(__name__)
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


@app.route('/stream')
@asyncio.coroutine
def stream():
    data = yield from message_stream()
    return flask.Response(data, mimetype="text/event-stream")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu/<template>')
def menu(template):
    return render_template('%s.html' % template)

@app.route('/today')
def today():
    return flask.jsonify(points=(yield from get_current_cost_data()))

@asyncio.coroutine
def setup_redis_connection():
    redis_conn = yield from create_redis_connection()
    app.config.update({'redis_connection': redis_conn})

@asyncio.coroutine
def setup_live_data_subscriber():
    redis_conn = yield from create_redis_connection()
    app.config.update({'live_data_subscriber':
                           RedisTimeCappedSubscriber(redis_conn, 'current_cost_live_data', 3600,pubsub_key=CURRENT_COST_KEY, indicator_key='watt').start()})

@app.route('/data_since/<seconds>')
def livedata(seconds):
    return flask.jsonify(points=app.config['live_data_subscriber'].get_data(since_seconds=int(seconds)))

@asyncio.coroutine
def get_current_cost_data():
    list_reply = yield from app.config['redis_connection'].lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1)
    l = yield from list_reply.aslist()
    return list(map(lambda json: loads(json, object_hook=with_iso8601_date), l))


if __name__ == '__main__':
    asyncio.async(setup_redis_connection())
    asyncio.async(setup_live_data_subscriber())
    app.run(host='0.0.0.0', threaded=True)
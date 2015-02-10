from datetime import datetime
from json import loads
from current_cost.sensor.current_cost import RedisSubscriber
import flask
from flask.templating import render_template
import redis

__author__ = 'bruno'

REDIS = redis.Redis()
app = flask.Flask(__name__)
now = datetime.now


def get_current_timestamp():
    return int(now().strftime('%s'))


class LiveDataMessageHandler(object):
    def __init__(self, myredis, message_period_in_minute=60):
        self.myredis = myredis
        self.history_duration_in_minute = message_period_in_minute

    def handle(self, json_message):
        timestamp = get_current_timestamp()
        self.myredis.zadd('current_cost_live', json_message, timestamp)
        self.myredis.zremrangebyscore('current_cost_live', 0, timestamp - self.history_duration_in_minute * 60)

    def get_data(self, since_minutes=60):
        return list(map(lambda json: loads(json.decode()),
                   self.myredis.zrangebyscore('current_cost_live', get_current_timestamp() - since_minutes * 60,
                                              get_current_timestamp())))


LIVE_DATA_MESSAGE_HANDLER = LiveDataMessageHandler(REDIS)


def message_stream():
    pubsub = REDIS.pubsub()
    pubsub.subscribe('current_cost')
    for message in pubsub.listen():
        yield 'data: %s\n\n' % message['data']


@app.route('/stream')
def stream():
    return flask.Response(message_stream(), mimetype="text/event-stream")


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/today')
def today():
    return flask.jsonify(points=get_current_cost_data())


@app.route('/data_since/<minutes>')
def livedata(minutes):
    return flask.jsonify(points=LIVE_DATA_MESSAGE_HANDLER.get_data(since_minutes=int(minutes)))


def get_current_cost_data():
    return list(map(lambda json: loads(json.decode()), REDIS.lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1)))


if __name__ == '__main__':
    RedisSubscriber(REDIS, LIVE_DATA_MESSAGE_HANDLER).start()
    app.run(host='0.0.0.0', threaded=True)
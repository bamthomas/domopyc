from datetime import datetime
from json import loads
import flask
from flask.templating import render_template
import redis
from current_cost import RedisSubscriber

__author__ = 'bruno'

REDIS = redis.Redis()
MESSAGES_PERIOD_IN_SECOND = 6.66
app = flask.Flask(__name__)

class LiveDataMessageHandler(object):
    def __init__(self, myredis, message_period_in_second=MESSAGES_PERIOD_IN_SECOND):
        self.myredis = myredis
        self.nb_messages_to_keep = 3600 / message_period_in_second

    def handle(self, json_message):
        self.myredis.lpush('current_cost_live', json_message)
        self.myredis.ltrim('current_cost_live', 0, self.nb_messages_to_keep-1)

    def get_data(self, since_minutes=60):
        nb_messages = since_minutes * 60  * self.nb_messages_to_keep / 3600
        return map(lambda json: loads(json), self.myredis.lrange('current_cost_live', 0, nb_messages-1))

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
    return map(lambda json: loads(json), REDIS.lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1))

if __name__ == '__main__':
    RedisSubscriber(REDIS, LIVE_DATA_MESSAGE_HANDLER).start()
    app.run(host='0.0.0.0', threaded=True)
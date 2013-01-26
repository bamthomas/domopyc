from datetime import datetime
from json import loads
import flask
from flask.templating import render_template
import redis

__author__ = 'bruno'

REDIS = redis.Redis()
app = flask.Flask(__name__)

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

def get_current_cost_data():
    return map(lambda json: loads(json), REDIS.lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1))

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', threaded=True)
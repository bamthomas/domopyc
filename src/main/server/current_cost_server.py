import flask
from flask.templating import render_template
import redis

__author__ = 'bruno'

REDIS = redis.Redis()
app = flask.Flask(__name__)

def event_stream():
    pubsub = REDIS.pubsub()
    pubsub.subscribe('current_cost')
    for message in pubsub.listen():
        yield 'data: %s\n\n' % message['data']

@app.route('/stream')
def stream():
    return flask.Response(event_stream(), mimetype="text/event-stream")

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', threaded=True)
from copy import copy
from datetime import datetime, timedelta
from json import loads, dumps
import flask
from flask.templating import render_template
import iso8601
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

def get_current_cost_data():
    return REDIS.lrange('current_cost_%s' % datetime.now().strftime('%Y-%m-%d'), 0, -1)

def fill_values(list, nb_data):
    if len(list) < nb_data:
        nb_per_intervall = nb_data / len(list)
        current_cost_data_dicts = map(lambda json: loads(json), list)
        result_list = []
        for item_dict in current_cost_data_dicts:
            item_date = iso8601.parse_date(item_dict['date'])
            minutes_in_intervall = item_dict['minutes'] / nb_per_intervall
            result_list.append(item_dict)
            for i in range(1, nb_per_intervall):
                copied_from_item = copy(item_dict)
                copied_from_item['date'] = (item_date + timedelta(minutes=minutes_in_intervall * i)).isoformat()
                result_list.append(copied_from_item)
        return map(lambda d: dumps(d), result_list)
    return list

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', threaded=True)
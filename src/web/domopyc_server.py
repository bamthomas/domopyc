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




if __name__ == '__main__':
    asyncio.async(setup_redis_connection())
    asyncio.async(setup_live_data_subscriber())
    app.run(host='0.0.0.0', threaded=True)
from datetime import datetime
import logging
import asyncio
from json import dumps, loads
from statistics import mean

from asyncio_redis.protocol import ZScoreBoundary
from iso8601_json import with_iso8601_date
import asyncio_redis
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport


root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')


def now(): return datetime.now()


@asyncio.coroutine
def create_redis_pool():
    connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=4)
    return connection


class RedisPublisher(object):
    RFXCOM_KEY = "rfxcom"

    def __init__(self, redis_conn):
        self.redis_conn = redis_conn

    @asyncio.coroutine
    def publish(self, event):
        yield from self.redis_conn.publish(self.RFXCOM_KEY, dumps(event))


class RedisTimeCappedSubscriber(object):
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_conn, indicator_name, max_data_age_in_seconds=0, pubsub_key=RedisPublisher.RFXCOM_KEY, indicator_key='temperature'):
        self.indicator_name = indicator_name
        self.indicator_key = indicator_key
        self.pubsub_key = pubsub_key
        self.max_data_age_in_seconds = max_data_age_in_seconds
        self.redis_conn = redis_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.redis_conn.start_subscribe()
        yield from self.subscriber.subscribe([self.pubsub_key])

    def start(self, for_n_messages=0):
        predicate = RedisTimeCappedSubscriber.infinite_loop if for_n_messages == 0 else RedisTimeCappedSubscriber.wait_value(for_n_messages)
        self.message_loop_task = asyncio.async(self.message_loop(predicate))
        return self

    @asyncio.coroutine
    def message_loop(self, predicate):
        i = 0
        while predicate(i):
            i += 1
            message_str = yield from self.subscriber.next_published()
            message = loads(message_str.value, object_hook=with_iso8601_date)
            yield from self.redis_conn.zadd(self.indicator_name, {str(message[self.indicator_key]): message['date'].timestamp()})
            if self.max_data_age_in_seconds:
                yield from self.redis_conn.zremrangebyscore(self.indicator_name, ZScoreBoundary('-inf'),
                                                            ZScoreBoundary(now().timestamp() - self.max_data_age_in_seconds))

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.redis_conn.zrange(self.indicator_name, 0, -1)
        d = yield from val.asdict()
        return mean((float(v) for v in list(d))) if d else 0.0


class RfxcomReader(object):
    def __init__(self, device, publisher, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        self.rfxcom_transport = self.create_transport(device, event_loop)

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(dict(packet.data, date=now().isoformat())))

    def default_callback(self, packet):
        logger.info('packet <%s> not handled' % packet)

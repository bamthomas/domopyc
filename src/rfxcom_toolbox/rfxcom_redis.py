from datetime import datetime
import logging
import asyncio
from json import dumps, loads
from statistics import mean

from asyncio_redis.protocol import ZScoreBoundary
import iso8601
import asyncio_redis
from rfxcom import protocol
from rfxcom.transport import AsyncioTransport


root = logging.getLogger()
logging.basicConfig()
root.setLevel(logging.INFO)

logger = logging.getLogger('rfxcom')


def now(): return datetime.now()


class RfxcomPoolTempSubscriber(object):
    key = 'pool_temperature'
    infinite_loop = lambda i: True
    wait_value = lambda n: lambda i: i < n

    def __init__(self, redis_conn, max_data_age_in_seconds=0):
        self.max_data_age_in_seconds = max_data_age_in_seconds
        self.redis_conn = redis_conn
        self.subscriber = None
        self.message_loop_task = None
        asyncio.new_event_loop().run_until_complete(self.setup_subscriber())

    @asyncio.coroutine
    def setup_subscriber(self):
        self.subscriber = yield from self.redis_conn.start_subscribe()
        yield from self.subscriber.subscribe([RedisPublisher.RFXCOM_KEY])

    def start(self, for_n_messages=0):
        predicate = RfxcomPoolTempSubscriber.infinite_loop if for_n_messages == 0 else RfxcomPoolTempSubscriber.wait_value(for_n_messages)
        self.message_loop_task = asyncio.async(self.message_loop(predicate))
        return self

    @asyncio.coroutine
    def message_loop(self, predicate):
        i = 0
        while predicate(i):
            i += 1
            message_str = yield from self.subscriber.next_published()
            message = loads(message_str.value)
            message['date'] = iso8601.parse_date(message['date'])
            yield from self.redis_conn.zadd(RfxcomPoolTempSubscriber.key, {str(message['temperature']): message['date'].timestamp()})
            if self.max_data_age_in_seconds:
                yield from self.redis_conn.zremrangebyscore(RfxcomPoolTempSubscriber.key, ZScoreBoundary('-inf'),
                                                            ZScoreBoundary(now().timestamp() - self.max_data_age_in_seconds))

    @asyncio.coroutine
    def get_average(self):
        val = yield from self.redis_conn.zrange(RfxcomPoolTempSubscriber.key, 0, -1)
        d = yield from val.asdict()
        return mean((float(v) for v in list(d))) if d else 0.0


class RedisPublisher(object):
    RFXCOM_KEY = "rfxcom"

    def __init__(self, host='localhost', port=6379):
        self.port = port
        self.host = host
        self.connection = None

    @asyncio.coroutine
    def redis_connect(self):
        self.connection = yield from asyncio_redis.Connection.create(self.host, self.port)

    @asyncio.coroutine
    def publish(self, event):
        if self.connection is None:
            yield from asyncio.wait_for(self.redis_connect(), timeout=5.0)
        yield from self.connection.publish(self.RFXCOM_KEY, dumps(event))


class RfxcomReader(object):
    def __init__(self, device, publisher, event_loop=asyncio.get_event_loop()):
        self.publisher = publisher
        self.rfxcom_transport = self.create_transport(device, event_loop)

    def create_transport(self, device, event_loop):
        return AsyncioTransport(device, event_loop,
                                callbacks={protocol.TempHumidity: self.handle_temp_humidity,
                                           '*': self.default_callback})

    def handle_temp_humidity(self, packet):
        asyncio.async(self.publisher.publish(packet.data))

    def default_callback(self, packet):
        logger.info('packet <%s> not handled' % packet)

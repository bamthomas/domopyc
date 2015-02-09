# coding=utf-8
from datetime import datetime, timedelta
from functools import reduce
from json import loads, dumps
import logging
import threading
import xml.etree.cElementTree as ET
import iso8601
import serial
import redis

CURRENT_COST = 'current_cost'
REDIS = redis.Redis()
__author__ = 'bruno'

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('current_cost')


def now(): return datetime.now()


class CurrentCostReader(threading.Thread):
    def __init__(self, serial_drv, publish_func):
        super(CurrentCostReader, self).__init__(target=self.read_sensor)
        self.serial_drv = serial_drv
        self.publish = publish_func
        self.stop_asked = threading.Event()

    def read_sensor(self):
        while not self.stop_asked.is_set():
            line = self.serial_drv.readline()
            if line:
                try:
                    xml_data = ET.fromstring(line)
                    power_element = xml_data.find('ch1/watts')
                    if power_element is not None:
                        power = int(power_element.text)
                        self.publish({'date': now().isoformat(), 'watt': power,
                                      'temperature': float(xml_data.find('tmpr').text)})
                except ET.ParseError as xml_parse_error:
                    LOGGER.exception(xml_parse_error)

    def stop(self):
        self.stop_asked.set()


def redis_publish(event_dict):
    REDIS.publish(CURRENT_COST, dumps(event_dict))


class RedisSubscriber(threading.Thread):
    def __init__(self, redis, message_handler):
        super(RedisSubscriber, self).__init__(target=self.wait_messages)
        self.message_handler = message_handler
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(CURRENT_COST)

    def wait_messages(self):
        for item in self.pubsub.listen():
            if item['type'] == 'message':
                self.message_handler.handle(item['data'])

    def stop(self):
        self.pubsub.unsubscribe(CURRENT_COST)


class AverageMessageHandler(object):
    def __init__(self, average_period_minutes=0):
        self.delta_minutes = timedelta(minutes=average_period_minutes)
        self.next_save_date = average_period_minutes == 0 and now() or self.next_plain(average_period_minutes, now())
        self.messages = []

    def next_plain(self, minutes, dt):
        return dt - timedelta(minutes=dt.minute % minutes - minutes, seconds=dt.second, microseconds=dt.microsecond)

    def handle(self, json_message):
        message = loads(json_message)
        self.messages.append(message)
        if now() >= self.next_save_date:
            self.save(iso8601.parse_date(message['date']), self.get_average_json_message(message['date']))
            self.next_save_date = self.next_save_date + self.delta_minutes
            self.messages = []

    def get_average_json_message(self, date):
        watt_and_temp = map(lambda msg: (msg['watt'], msg['temperature']), self.messages)

        def add_tuple(x_t, y_v):
            x, t = x_t
            y, v = y_v
            return x + y, t + v

        watt_sum, temp_sum = reduce(add_tuple, watt_and_temp)
        nb_messages = len(self.messages)
        return {'date': date, 'watt': watt_sum / nb_messages, 'temperature': temp_sum / nb_messages,
                'nb_data': nb_messages, 'minutes': int(self.delta_minutes.total_seconds() / 60)}

    def save(self, message_date, average_message):
        raise NotImplementedError


class RedisAverageMessageHandler(AverageMessageHandler):
    def __init__(self, db, average_period_minutes=0):
        super(RedisAverageMessageHandler, self).__init__(average_period_minutes)
        self.redis = db

    def save(self, message_date, average_message):
        key = 'current_cost_%s' % message_date.strftime('%Y-%m-%d')
        if self.redis.lpush(key, dumps(average_message)) == 1:
            self.redis.expire(key, 5 * 24 * 3600)


class MysqlAverageMessageHandler(AverageMessageHandler):
    CREATE_TABLE_SQL = '''CREATE TABLE IF NOT EXISTS `current_cost` (
                            `id` mediumint(9) NOT NULL AUTO_INCREMENT,
                            `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            `watt` int(11) DEFAULT NULL,
                            `minutes` int(11) DEFAULT NULL,
                            `nb_data` int(11) DEFAULT NULL,
                            `temperature` float DEFAULT NULL,
                            PRIMARY KEY (`id`)
                            ) ENGINE=MyISAM DEFAULT CHARSET=utf8'''

    def __init__(self, db, average_period_minutes=0):
        super(MysqlAverageMessageHandler, self).__init__(average_period_minutes)
        self.db = db
        with self.db:
            self.db.cursor().execute(MysqlAverageMessageHandler.CREATE_TABLE_SQL)

    def save(self, message_date, average_message):
        with self.db:
            self.db.cursor().execute(
                "INSERT INTO current_cost (timestamp, watt, minutes, nb_data, temperature) values ('%s', %s, %s, %s, %s) " % (
                    message_date, average_message['watt'], average_message['minutes'], average_message['nb_data'],
                    average_message['temperature']))


if __name__ == '__main__':
    serial_drv = serial.Serial('/dev/ttyUSB0', baudrate=57600,
                               bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                               timeout=10)
    try:
        current_cost = CurrentCostReader(serial_drv, redis_publish)
        current_cost.start()

        redis_save_consumer = RedisSubscriber(REDIS, RedisAverageMessageHandler(REDIS, 10))
        redis_save_consumer.start()

        current_cost.join()
    finally:
        serial_drv.close()

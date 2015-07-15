from datetime import timedelta, datetime
from json import loads
import asyncio
from operator import itemgetter
from statistics import mean
from domopyc.iso8601_json import with_iso8601_date
from tzlocal import get_localzone


def now(): return datetime.now(tz=get_localzone())

class AverageMemoryMessageHandler(object):
    def __init__(self, keys, average_period_minutes=0):
        self.keys = keys
        self.delta_minutes = timedelta(minutes=average_period_minutes)
        self.next_save_date = average_period_minutes == 0 and now() or self.next_plain(average_period_minutes, now())
        self.messages = []

    @staticmethod
    def next_plain(minutes, dt):
        return dt - timedelta(minutes=dt.minute % minutes - minutes, seconds=dt.second, microseconds=dt.microsecond)

    def handle(self, json_message):
        message = loads(json_message, object_hook=with_iso8601_date)
        self.messages.append(message)
        if now() >= self.next_save_date:
            average_json_message = self.get_average_json_message(message['date'])
            self.next_save_date = self.next_save_date + self.delta_minutes
            self.messages = []
            return asyncio.async(self.save(average_json_message))

    def get_average_json_message(self, date):
        keys_mean = map(mean, zip(*map(itemgetter(*self.keys), self.messages)))
        dict_mean = dict(zip(self.keys, keys_mean))
        return dict(date=date, nb_data=len(self.messages), minutes=int(self.delta_minutes.total_seconds() / 60), **dict_mean)

    @asyncio.coroutine
    def save(self, average_message):
        raise NotImplementedError

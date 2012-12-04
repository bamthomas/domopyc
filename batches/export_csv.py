from datetime import datetime, timedelta
from json import loads
from posixpath import join
import redis

__author__ = 'bruno'

REDIS = redis.Redis()

class ExportBatch(object):

    def __init__(self, date = datetime.now() - timedelta(days=1)):
        self.key = 'current_cost_%s' % date.strftime('%Y-%m-%d')

    def create_csv_file(self):
        file_name = join('/tmp','%s.csv' % self.key)
        with open(file_name, mode='w') as csv:
            json_message = REDIS.lpop(self.key)
            message = loads(json_message)
            self.add_headers(csv, message)
            csv.write(';'.join([str(v) for v in message.values()]) + '\n')
            while json_message is not None:
                json_message = REDIS.lpop(self.key)
                if json_message: 
		    csv.write(';'.join([str(v) for v in loads(json_message).values()]) + '\n')
        return file_name

    def add_headers(self, csv, message):
        csv.write(';'.join(message.keys())+ '\n')

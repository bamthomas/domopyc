from datetime import datetime, timedelta
from ftplib import FTP
from json import loads
import os
from posixpath import join, basename
import redis

__author__ = 'bruno'

REDIS = redis.Redis()
USER = 'current_cost'
PASS = 'current_cost'
DIR  = 'current_cost'
HOST = '192.168.0.10'
PORT = 21

class ExportBatch(object):

    def __init__(self, date = datetime.now() - timedelta(days=1)):
        self.key = 'current_cost_%s' % date.strftime('%Y-%m-%d')

    def create_csv_file(self):
        file_name = join('/tmp','%s.csv' % self.key)

        if REDIS.type(self.key) != 'list':
            if os.path.isfile(file_name):
                return file_name
            else: return None

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

    def ftp_send(self, file_name, host=HOST, port=PORT, user=USER, passwd=PASS, dir=DIR):
        if file_name is None: return
        ftp = FTP()
        try:
            ftp.connect(host=host, port=port)
            ftp.login(user=user, passwd=passwd)
            with open(file_name, mode='r') as csv:
                ftp.storlines('STOR %s' % join(dir, basename(file_name)), csv)
        finally:
            ftp.close()

if __name__ == '__main__':
    for days_before in xrange(1, 5):
        batch = ExportBatch(date=datetime.now() - timedelta(days=days_before))
        file_name = batch.create_csv_file()
        batch.ftp_send(file_name)


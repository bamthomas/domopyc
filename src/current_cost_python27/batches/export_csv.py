from datetime import datetime, timedelta
from ftplib import FTP
from json import loads
import os
import csv
from posixpath import join, basename
import redis

__author__ = 'bruno'

REDIS = redis.Redis()
USER = 'current_cost'
PASS = 'current_cost'
DIR  = 'current_cost'
HOST = '192.168.0.10'
PORT = 21


class ExcelSemicolon(csv.excel):
    delimiter = ';'


class ExportBatch(object):

    def __init__(self, date = datetime.now() - timedelta(days=1)):
        self.key = 'current_cost_%s' % date.strftime('%Y-%m-%d')

    def create_csv_file(self):
        filename = join('/tmp', '%s.csv' % self.key)

        if REDIS.type(self.key) != b'list':
            if os.path.isfile(filename):
                return filename
            else:
                return None

        with open(filename, 'w', newline='') as csvfile:
            json_message = REDIS.lpop(self.key)
            message = loads(json_message.decode())
            csvwriter = csv.DictWriter(csvfile, dialect=ExcelSemicolon, fieldnames=sorted(message.keys()))
            csvwriter.writeheader()
            csvwriter.writerow(message)
            while json_message is not None:
                json_message = REDIS.lpop(self.key)
                if json_message:
                    csvwriter.writerow(loads(json_message.decode()))
        return filename

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
    for days_before in range(1, 5):
        batch = ExportBatch(date=datetime.now() - timedelta(days=days_before))
        file_name = batch.create_csv_file()
        batch.ftp_send(file_name)
        if file_name: os.remove(file_name)


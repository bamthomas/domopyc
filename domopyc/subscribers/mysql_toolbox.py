# coding=utf-8
import logging
import asyncio

from domopyc.subscribers.toolbox import AverageMemoryMessageHandler

logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
LOGGER = logging.getLogger('domopyc')


class MysqlCurrentCostMessageHandler(AverageMemoryMessageHandler):
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
        super(MysqlCurrentCostMessageHandler, self).__init__(['watt', 'temperature'], average_period_minutes)
        self.db = db
        asyncio.async(self.setup_db())

    @asyncio.coroutine
    def setup_db(self):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute(MysqlCurrentCostMessageHandler.CREATE_TABLE_SQL)
            yield from cur.fetchone()
            yield from cur.close()

    @asyncio.coroutine
    def save(self, average_message):
        with (yield from self.db) as conn:
            cursor = yield from conn.cursor()
            yield from cursor.execute(
                'INSERT INTO current_cost (timestamp, watt, minutes, nb_data, temperature) values (\'%s\', %s, %s, %s, %s) ' % (
                    average_message['date'].strftime('%Y-%m-%d %H:%M:%S'), average_message['watt'], average_message['minutes'],
                    average_message['nb_data'],
                    average_message['temperature']))
            yield from cursor.close()


class MysqlTemperatureMessageHandler(AverageMemoryMessageHandler):
    CREATE_TABLE_SQL = '''CREATE TABLE IF NOT EXISTS `%s` (
                                `id` mediumint(9) NOT NULL AUTO_INCREMENT,
                                `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                `temperature` float DEFAULT NULL,
                                `minutes` int(11) DEFAULT NULL,
                                `nb_data` int(11) DEFAULT NULL,
                                PRIMARY KEY (`id`)
                                ) ENGINE=MyISAM DEFAULT CHARSET=utf8'''

    def __init__(self, db, table_name, average_period_minutes=0):
        super().__init__(['temperature'], average_period_minutes)
        self.table_name = table_name
        self.db = db
        asyncio.async(self.setup_db())

    @asyncio.coroutine
    def setup_db(self):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute(MysqlTemperatureMessageHandler.CREATE_TABLE_SQL % self.table_name)
            yield from cur.fetchone()
            yield from cur.close()

    @asyncio.coroutine
    def save(self, average_message):
        with (yield from self.db) as conn:
            cursor = yield from conn.cursor()
            yield from cursor.execute(
                'INSERT INTO {table_name} (timestamp, temperature, minutes, nb_data) values (%s, %s, %s, %s)'.format(
                    table_name=self.table_name), (
                    average_message['date'].strftime('%Y-%m-%d %H:%M:%S'),
                    average_message['temperature'],
                    average_message['minutes'],
                    average_message['nb_data']))
            yield from cursor.close()

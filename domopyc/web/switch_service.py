# coding=utf-8
import asyncio


class SwichService(object):
    CREATE_TABLE_SQL = '''CREATE TABLE IF NOT EXISTS `domopyc_switch` (
                               `id` char(7) NOT NULL,
                               `label` VARCHAR(255),
                               `state` TINYINT(1) DEFAULT 0,
                               PRIMARY KEY (`id`)
                               ) ENGINE=MyISAM DEFAULT CHARSET=utf8'''

    def __init__(self, mysql_pool):
        self.db = mysql_pool
        asyncio.async(self.init_table())

    @asyncio.coroutine
    def insert(self, id, label):
        int(id, 16)
        if len(id) != 7:
            raise ValueError("len of id must be 7 hexa char")
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute("INSERT INTO domopyc_switch (id, label) VALUES (%s, %s)", (id, label))
            yield from cur.close()

    @asyncio.coroutine
    def get_all(self):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute('SELECT id, label, state FROM domopyc_switch')
            result = yield from cur.fetchall()
            yield from cur.close()
            return {'switches': [{'id': row[0], 'label': row[1], 'state': row[2]} for row in result]}

    @asyncio.coroutine
    def init_table(self):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute(SwichService.CREATE_TABLE_SQL)
            yield from cur.fetchone()
            yield from cur.close()

    @asyncio.coroutine
    def delete(self, id):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute('DELETE FROM domopyc_switch WHERE id=%s', id)
            yield from cur.close()

    @asyncio.coroutine
    def switch(self, id, on_off):
        with (yield from self.db) as conn:
            cur = yield from conn.cursor()
            yield from cur.execute('UPDATE domopyc_switch SET state=%s WHERE ID=%s', (on_off, id))
            yield from cur.fetchone()
            yield from cur.close()

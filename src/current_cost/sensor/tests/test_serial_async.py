from socket import socketpair
import asyncio
import pty
import os
from serial import Serial


class DummySerialWithSocket():
    # you should consider subclassing this
    def __init__(self, *args, **kwargs):
        self.rsock, self.wsock = socketpair()
        self.fd = self.rsock

    def read(self, bytes=1):
        return self.rsock.recv(bytes)

    def write(self, data):
        self.wsock.send(data)

    def close(self):
        self.wsock.close()
        self.rsock.close()


class DummySerialWithPtmx():
    # you should consider subclassing this
    def __init__(self, *args, **kwargs):
        self.tty_master, self.tty_slave = pty.openpty()
        s_name = os.ttyname(self.tty_slave)
        self.ser = Serial(s_name)
        self.fd = self.tty_slave

    def read(self, bytes=1):
        return os.read(self.tty_master, bytes)

    def write(self, data):
        self.ser.write(data)

    def close(self):
        self.ser.close()

driver = DummySerialWithSocket()


class MyDriver(object):

    def __init__(self, drv):
        self.drv = drv
        asyncio.get_event_loop().add_reader(self.drv.fd, self.read_loop)

    def read_loop(self):
        r = "continue"
        while r == "continue":
            nb_bytes = 6
            print("reading %s bytes" % nb_bytes)
            r = self.drv.read(nb_bytes)
            print("read from serial : %s" % r)

# tty_master, tty_slave = pty.openpty()
# s_name = os.ttyname(tty_slave)
# m_name = os.ttyname(tty_master)

# print('master=%s slave=%s' % (m_name, s_name))
# slave = Serial(s_name)
# master = Serial(m_name)

print("callback")
d = MyDriver(driver)
asyncio.get_event_loop().add_reader(driver.fd, d.read_loop)
# t = threading.Thread(target=read_loop, kwargs={'dev': driver})
# print("starting thread")
# t.start()

print("writing to serial")
driver.write('coucou'.encode())

asyncio.get_event_loop().run_forever()


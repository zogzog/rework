import os
from threading import Thread
import socket
import time
import logging
from datetime import datetime

import pytz
import psutil

from rework.schema import log


def utcnow():
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def memory_usage(pid):
    process = psutil.Process(pid)
    return int(process.memory_info().rss / float(2 ** 20))


def wait_true(func, timeout=6):
    outcome = []

    def loop():
        start = time.time()
        while True:
            if (time.time() - start) > timeout:
                return
            output = func()
            if output:
                outcome.append(output)
                return
            time.sleep(.1)

    th = Thread(target=loop)
    th.daemon = True
    th.start()
    th.join()
    assert outcome
    return outcome[0]


def guard(engine, sql, expr, timeout=6):

    def check():
        with engine.begin() as cn:
            return expr(cn.execute(sql))

    return wait_true(check, timeout)


def host():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    return s.getsockname()[0]


def kill(pid, timeout=3):
    def on_terminate(proc):
        print('process {} terminated with exit code {}'.format(proc, proc.returncode))

    # TERM then KILL
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        _, alive = psutil.wait_procs([proc], timeout=timeout, callback=on_terminate)
        if alive:
            proc.kill()
            _, alive = psutil.wait_procs([proc], timeout=timeout, callback=on_terminate)
            if alive:
                return False
    except psutil.NoSuchProcess:
        return True
    return True


def has_ancestor_pid(pid):
    parent = psutil.Process(os.getpid()).parent()
    while parent:
        if pid == parent.pid:
            return True
        parent = parent.parent()
    return False


def kill_process_tree(pid, timeout=3):
    """Terminate all the children of this process.
    inspired from https://psutil.readthedocs.io/en/latest/#terminate-my-children
    """
    try:
        procs = psutil.Process(pid).children()
    except psutil.NoSuchProcess:
        print('process {} is already dead'.format(pid))
        return True
    for proc in procs:
        kill_process_tree(proc.pid, timeout)
        kill(proc.pid)
    return kill(pid)

# Logging


class PGLogHandler(logging.Handler):
    maxqueue = 100

    def __init__(self, task, sync=True):
        super(PGLogHandler, self).__init__()
        self.task = task
        self.sync = sync
        self.lastflush = time.time()
        self.queue = []
        self.formatter = logging.Formatter(
            '%(name)s:%(levelname)s: %(asctime)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def emit(self, record):
        self.queue.append(record)

        if ((time.time() - self.lastflush) > 1 or
            len(self.queue) > self.maxqueue):
            self.flush()

    def flush(self):
        if not self.queue:
            return

        values = [{'task': self.task.tid,
                   'tstamp': record.created,
                   'line': self.formatter.format(record)}
                  for record in self.queue]
        self.queue = []
        self.lastflush = time.time()

        def writeback_log(values, engine):
            sql = log.insert().values(values)
            with engine.begin() as cn:
                cn.execute(sql)

        th = Thread(target=writeback_log,
                    args=(values, self.task.engine))
        th.daemon = True
        # fire and forget
        th.start()
        if self.sync:
            th.join()

    def close(self):
        pass


class PGLogWriter(object):
    __slots__ = ('stream', 'handler', 'level', 'pending')

    def __init__(self, stream, handler):
        self.stream = stream
        self.handler = handler
        if 'out' in self.stream:
            self.level = logging.INFO
        else:
            self.level = logging.WARNING
        self.pending = []

    def write(self, message):
        linefeed = '\n' in message
        if not linefeed and not message.strip():
            return
        self.pending.append(message)
        if linefeed:
            self.flush()

    def flush(self):
        message = ''.join(msg for msg in self.pending)
        if not '\n' in message:
            return
        self.pending = []
        if message:
            for part in message.strip().split('\n'):
                self.handler.emit(
                    logging.LogRecord(
                        self.stream, self.level, '', -1, part, (), ()
                    )
                )

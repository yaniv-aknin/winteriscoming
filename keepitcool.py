import errno
import json
import logging
import os
import socket
import subprocess
import sys
import time

def is_connected_to_terminal():
    return os.isatty(sys.stdin.fileno())

if is_connected_to_terminal():
    logging.basicConfig(level=logging.INFO)
else:
    logging.getLogger().addHandler(logging.NullHandler())

class CoolKeeper(object):
    WARNING_THRESHOLD = 35
    ERROR_THRESHOLD = 40
    FATAL_THRESHOLD = 45

    LOCK_FILE='/var/lock/coolkeeper.lock'

    OUTPUT_LOCK_INTERVAL = 60 * 60 * 4
    def __init__(self, host='localhost', port=7634):
        self.host = host
        self.port = port
        self.warning = False
        self.error = 0
        self.fatal = False
        self.output = []
        self.raw = None
        self.disks = {}

    def run(self):
        logging.info('%s starting', self.__class__.__name__)
        try:
            self.get_reading_with_retries()
            self.parse_reading()
            self.evaluate_status()
        except (socket.error, ValueError):
            self.output = ['ERROR: Unable to get reading!']
            self.warning = True
        self.perform_required_actions()
        logging.info('%s finished', self.__class__.__name__)

    def get_reading_with_retries(self):
        for retry in range(3):
            self.get_reading()
            if self.raw and len(self.raw) > 1:
                break
            time.sleep(3)

    def get_reading(self):
        BUFFER_SIZE = 4096
        handle = socket.socket()
        handle.connect((self.host, self.port))
        buf = [handle.recv(BUFFER_SIZE)]
        while len(buf[-1]) == BUFFER_SIZE:
            buf.append(handle.recv(BUFFER_SIZE))
        self.raw = "".join(buf)

    def parse_reading(self):
        readings = self.raw.split('||')
        for reading in readings:
            device, description, temperature, units = reading.strip('|').split('|')
            self.disks[(device, description)] = temperature
            logging.info('%s (%s) -> %s', device, description, temperature)

    def evaluate_status(self):
        for (disk, name), temperature in self.disks.iteritems():
            try:
                temperature = int(temperature)
                if temperature >= self.WARNING_THRESHOLD:
                    self.output.append('ERROR: %s (%s) is at %d degrees!' % (disk, name, temperature))
                    self.warning = True
                if temperature >= self.ERROR_THRESHOLD:
                    self.error += 1
                if temperature >= self.FATAL_THRESHOLD:
                    self.fatal = True
            except ValueError:
                self.output.append('ERROR: %s (%s) is unreadable!' % (disk, name, temperature))
                self.error += 1

    def perform_required_actions(self):
        if self.warning:
            if self.raw is not None:
                self.output.append('')
                self.output.append('raw output: %s' % (repr(self.raw)[:512],))
            self.output.append('')
            if self.allowed_to_write_output():
                sys.stderr.write("\n".join(self.output))
        if self.error > 1:
            self.fatal = True
        if self.fatal:
            self.shutdown()


    def allowed_to_write_output(self):
        if is_connected_to_terminal():
            return True
        try:
            result = os.stat(self.LOCK_FILE)
            if time.time() - result.st_mtime < self.OUTPUT_LOCK_INTERVAL:
                return False
        except OSError, error:
            if error.errno == errno.ENOENT:
                with file(self.LOCK_FILE, 'a'):
                    os.utime(self.LOCK_FILE, None)
        return True
    def shutdown(self):
        subprocess.Popen(['shutdown', '-P', '+1', 'System powering off to protect disks'])

def main(argv):
    keeper = CoolKeeper()
    keeper.run()
    if keeper.warning:
        raise SystemExit(1)

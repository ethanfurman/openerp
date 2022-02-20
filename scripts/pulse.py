#!/usr/bin/env python2
"""Pulse HTTP Server.

This module builds an HTTP logging server.  Requests are logged as usual and
the log file can be parsed by other tools.

"""
from __future__ import print_function
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from traceback import format_exception
from urlparse import urlparse, parse_qs
import io
import os
import shutil
import sys
import threading
import time

from scription import *

__version__ = "0.1"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):

    allow_reuse_address = 1
    is_empty_log = False
    log_name = None
    log_file = None
    log_lock = threading.Lock()

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, log_file=None, msg_location=None):
        self.msg_location = msg_location or os.getcwd()
        self.today = time.localtime(time.time())[:3]
        self.log_name = log_file
        self.prep_log_file()
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)

    def prep_log_file(self):
        if self.log_name is None:
            return
        dirs, filename = os.path.split(self.log_name)
        if not os.path.exists(dirs):
            os.path.mkdirs(dirs)
        if not os.path.exists(self.log_name):
            self.log_file = io.open(self.log_name, 'w', encoding='utf-8')
            self.is_empty_log = True

    def emit_message(self, msg, timestamp):
        with self.log_lock:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
            if self.log_file is None:
                stderr.write(msg)
            else:
                # time to rotate the file?
                if not self.is_empty_log and self.today != time.localtime(timestamp)[:3]:
                    new_name = '%s.%s%s%s' % ((self.log_name, ) + self.today)
                    self.log_file.close()
                    shutil.move(self.log_name, new_name)
                    self.log_file = io.open(self.log_name, 'w', encoding='utf-8')
                self.log_file.write(msg)

    def handle_error(self, request, client_address):
        cls, exc, tb = sys.exc_info()
        frames = format_exception(cls, exc, tb)
        keep = False
        lines = []
        for f in frames:
            if keep or 'pulse.pyz' in f:
                keep = True
                lines.append(f)
        error(''.join(lines).strip(), border='box')




class PulseHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Pulse HTTP request handler with the GET command.
    """

    server_version = "PulseHTTP/" + __version__
    protocol_version = 'HTTP/1.0'

    def do_GET(self):
        self.send_response(204)
        self.end_headers()
        self.wfile.flush() # send the response
        data = urlparse(self.path.decode('utf-8'))
        self.create_message_file(data)

    def do_POST(self):
        self.send_response(204)
        self.end_headers()
        self.wfile.flush() # send the response
        data = urlparse(self.path.decode('utf-8'))
        query = parse_qs(self.rfile.read().decode('utf-8'))
        self.create_message_file(data, query)

    def create_message_file(self, data, query=None):
        if query is None:
            query = parse_qs(data.query)
        _, ip, freq, name = data.path.split(u'/', 3)
        msg_file_name = u'IP-%s-%s-%02d%02d-%05d.txt' % ((ip, name) + self.server.today[1:] + (next(counter), ))
        # main portion of data for message file
        msg_file_data = [
            "{",
            "'ip_address': %r," % ip,
            "'job_name': %r," % name,
            "'frequency': %r," % freq,
            ]
        # possible query parameters
        for key, value in query.items():
            msg_file_data.append("'%s': %r," % (key, value[0]))
        msg_file_data.append("}\n")
        msg_file_data = '\n'.join(msg_file_data).decode('utf-8')
        with io.open(self.server.msg_location+'/'+msg_file_name, 'w', encoding='utf-8') as f:
            f.write(msg_file_data)

    def log_message(self, format, *args):
        """
        Log an arbitrary message.
        """
        timestamp = time.time()
        message = "%s - - [%s] %s\n" % (
                self.client_address[0],
                self.log_date_time_string(timestamp),
                format % args)
        self.server.emit_message(message, timestamp)

    def log_date_time_string(self, timestamp=None):
        """
        Return the current time formatted for logging.
        """
        if timestamp is None:
            timestamp = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(timestamp)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
                day, self.monthname[month], year, hh, mm, ss)
        return s




@Command(
        port=Spec('port to serve on', type=int),
        log_file=Spec('name of file to log to [default: stderr]', OPTION),
        msg_location=Spec('location to write message files', OPTION),
        )
def serve(port, log_file, msg_location):
    """
    Run an HTTP server on PORT with logging to LOG-FILE
    """
    global counter
    def counter():
        counter_file = (msg_location or os.getcwd()) + '/counter'
        if os.path.exists(counter_file):
            with open(counter_file) as f:
                i = int(f.read()) + 100
        else:
            i = 0
        lock = threading.Lock()
        while True:
            with lock:
                i += 1
                i %= 10000
                if i % 100 == 0:
                    # write count
                    with open(counter_file, 'w') as f:
                        f.write(str(i))
                yield i 
    counter = counter()

    server_address = ('', port)

    httpd = ThreadingHTTPServer(
            server_address,
            PulseHTTPRequestHandler,
            log_file=log_file,
            msg_location=msg_location,
            )

    sa = httpd.socket.getsockname()
    echo("Serving HTTP on", sa[0], "port", sa[1], "...")
    httpd.serve_forever()


Run()

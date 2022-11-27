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
from datetime import datetime
import io
import os
import re
import shutil
import sys
import threading
import time

from scription import *

__version__ = "0.11"


# server

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):

    allow_reuse_address = 1
    is_empty_log = False
    log_name = None
    log_file = None
    log_lock = threading.Lock()

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, log_file=None, msg_location=None):
        self.msg_location = msg_location or os.getcwd()
        self.log_name = log_file
        self.prep_log_file()
        self.today = time.localtime(time.time())[:3]
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)

    def prep_log_file(self):
        if self.log_name is None:
            return
        dirs, filename = os.path.split(self.log_name)
        if not os.path.exists(dirs):
            os.path.mkdirs(dirs)
        if not os.path.exists(self.log_name):
            self.is_empty_log = True
        self.log_file = io.open(self.log_name, 'a', encoding='utf-8')

    def emit_message(self, msg, timestamp):
        with self.log_lock:
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8')
            if self.log_file is None:
                stderr.write(msg)
            else:
                # time to rotate the file?
                now = time.localtime(timestamp)[:3]
                if not self.is_empty_log and self.today != now:
                    self.log_file.close()
                    new_name = '%s.%04d%02d%02d' % ((self.log_name, ) + self.today)
                    dirs, filename = os.path.split(self.log_name)
                    shutil.move(self.log_name, os.path.join(dirs, new_name))
                    self.log_file = io.open(self.log_name, 'a', encoding='utf-8')
                    self.today = now
                self.log_file.write(msg)
                self.log_file.flush()

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
        timestamp = time.localtime(time.time())
        msg_file_name = self.server.msg_location + '/' + 'IP-%s-%s-%04d%02d%02d_%02d%02d%02d' % ((ip, name, ) + timestamp[:6])
        # main portion of data for message file
        msg_file_data = [
            "{",
            "'ip_address': %r," % ip,
            "'job_name': %r," % name,
            "'frequency': %r," % freq,
            "'timestamp': (%d, %d, %d, %d, %d, %d)," % timestamp[:6],
            ]
        # possible query parameters
        for key, value in query.items():
            msg_file_data.append("'%s': %r," % (key, value[0]))
        msg_file_data.append("}\n")
        msg_file_data = '\n'.join(msg_file_data).decode('utf-8')
        with io.open(msg_file_name+'.tmp', 'w', encoding='utf-8') as f:
            f.write(msg_file_data)
        shutil.move(msg_file_name+'.tmp', msg_file_name+'.txt')

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


# API

@Command(
        port=Spec('port to serve on', type=int),
        log_file=Spec('name of file to log to [default: stderr]', OPTION),
        msg_location=Spec('location to write message files', OPTION),
        )
def serve(port, log_file, msg_location):
    """
    Run an HTTP server on PORT with logging to LOG-FILE
    """
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


@Command(
        log_file=Spec('name of file to log to [default: stderr]', ),
        msg_location=Spec('location to write message files', ),
        )
def parse_log(log_file, msg_location):
    """
    scan a log file and create message files from its entries (any POST parameters are lost)
    """
    match = Var(re.search)
    with open(log_file) as log:
        for line in log.readlines():
            if match(r'\[(\d\d/\w\w\w/\d\d\d\d \d\d:\d\d:\d\d)\] "GET /(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/(\w+)/(.*) HTTP.*"', line):
                timestamp, ip, freq, name = match().groups()
                timestamp = datetime.strptime(timestamp, '%d/%b/%Y %H:%M:%S')
                msg_file_name = timestamp.strftime('IP-%%s-%%s-%Y%m%d_%H%M%S.txt') % (ip, name, )
                # main portion of data for message file
                msg_file_data = [
                    "{",
                    "'ip_address': %r," % ip,
                    "'job_name': %r," % name,
                    "'frequency': %r," % freq,
                    "'timestamp': %r," % timestamp,
                    "}\n"
                    ]
                msg_file_data = '\n'.join(msg_file_data).decode('utf-8')
                with io.open(msg_location+'/'+msg_file_name, 'w', encoding='utf-8') as f:
                    f.write(msg_file_data)
            else:
                error('unable to parse line %r' % line)


Run()

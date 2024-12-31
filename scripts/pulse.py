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
import textwrap
import threading
import time

from scription import *

__version__ = "0.11"


## server

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    #
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
        timestamp = time.time()
        cls, exc, tb = sys.exc_info()
        frames = format_exception(cls, exc, tb)
        keep = False
        lines = []
        for f in frames:
            if keep or 'pulse.pyz' in f:
                keep = True
                lines.append(f)
        if self.log_file is not None:
            error(''.join(lines).strip(), border='box')
        lines.insert(0, '-'*50+'\n')
        lines.append('-'*50+'\n')
        self.emit_message(''.join(lines).strip()+'\n', timestamp)


class PulseHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Pulse HTTP request handler with the GET command.
    """

    server_version = "PulseHTTP/" + __version__
    protocol_version = 'HTTP/1.0'

    def do_HELP(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/markdown')
        self.send_header('Content-Length', len(help_md))
        self.end_headers()
        self.wfile.write(help_md)
        self.wfile.flush()

    def do_GET(self):
        try:
            data = urlparse(self.path.decode('utf-8').replace('//','/'))
            # e.g. ParseResult(
            #           scheme='', netloc='',
            #           path='/192.168.11.1/weekly//linuxworkstationsync-192.168.11.193',
            #           params='', query='', fragment='',
            #           )
            if data.path == '/help':
                self.do_HELP()
                return
            else:
                self.create_message_file(data)
        except HandledError:
            self.send_response(400)
            self.end_headers()
            self.wfile.flush() # send the response
        except:
            self.send_response(500)
            self.end_headers()
            self.wfile.flush() # send the response
            raise
        else:
            self.send_response(204)
            self.end_headers()
            self.wfile.flush() # send the response

    def do_POST(self):
        try:
            data = urlparse(self.path.decode('utf-8')).replace('//','/')
            query = parse_qs(self.rfile.read().decode('utf-8'))
            self.create_message_file(data, query)
        except HandledError:
            self.send_response(400)
            self.end_headers()
            self.wfile.flush() # send the response
        except:
            self.send_response(500)
            self.end_headers()
            self.wfile.flush() # send the response
            raise
        else:
            self.send_response(204)
            self.end_headers()
            self.wfile.flush() # send the response

    def create_message_file(self, data, query=None):
        if query is None:
            query = parse_qs(data.query)
        try:
            _, ip, freq, name = data.path.split(u'/', 3)
        except ValueError:
            self.log_message('invalid pulse %r', data.path)
            raise HandledError
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
        try:
            with io.open(msg_file_name+'.tmp', 'w', encoding='utf-8') as f:
                f.write(msg_file_data)
        except IOError:
            self.log_message('unable to save file %r', msg_file_name+'.tmp')
            raise HandledError
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


class HandledError(Exception):
    pass

help_md = textwrap.dedent("""\
        ===================
        Pulse Specification
        ===================

        Tracking
        ========

        - frequency -- jobs occur as expected
          - continuous (multiple times per hour)
          - intermittent (multiple times per day)
          - daily
          - weekly
          - monthly
          - quarterly
          - yearly
          - urgent

        - device
          - 11.16
          - 11.111

        - job
          - sync
          - backup

        and eventually

        - status
          - pass/fail
          - percentage
          - text
          - tripline
        - etc.


        Communication
        =============

        Network
        -------

        A web server[^1] will run on `11.16` at port `3500`, and will accept `GET`
        requests as a form of heart beat.  Those requests are logged, processed, and a
        `204`[^2] code returned.

        `GET` requests take the form of:

            $ curl -s http://192.168.11.16:3500/192.168.8.8/weekly/full_backup
                      \  the pulse server     /\ reporting |   \      \ the pulse name
                                                \  machine |    \\
                                                                 \  daily, weekly, etc.

        `POST` requests are also accepted, although at this point they are only useful
        for `urgent` frequency messages.  For example:

            # set status to FIX and send messages
            $ curl http://127.0.0.1:8000/192.168.11.16/urgent/backup -d action=alert

            # set status to FIX
            $ curl http://127.0.0.1:8000/192.168.11.16/urgent/backup -d action=trip

            # remove PULSE from clues, set status to GOOD if no other warnings exist
            $ curl http://127.0.0.1:8000/192.168.11.16/urgent/backup -d action=clear

        If the `action` parameter is left off, the default action is `trip` (no messages
        sent, just change the status).


        Web Server
        ----------

        Besides the log file[^3] (which can be parsed by other tools), the web server
        will write message files[^4].  When running in production mode, these files
        must be written to the openerp server at:

            /home/openerp/sandbox/openerp/var/pulse

        These files will be named using the first and third pieces of the request -- so
        typically the reporting machine's IP address and job name.  The contents of these
        files will repeat the IP address and job name, and will additionally have the
        frequency; if `POST` is used, the fields in the `POST` request will also be in
        the message file.

        Continuing the first example:

            # file name: IP-192.168.8.8-full_backup.txt
            {
            "ip_address": "192.168.8.8",
            "job_name": "full_backup",
            "frequency": "weekly",
            }


        OpenERP Server
        --------------

        An OpenERP cron job will monitor the above directory and update the appropriate
        tables with the information found in the message files.  Another OpenERP cron
        job will check for missing entries, and change the status of the IP device to
        `FIX` if sufficient time has passed:

          - continuous jobs have grace periods of 30 minutes
          - intermittent jobs have grace periods of 60 minutes during business hours
            (defined as 05:00 - 18:00)
          - all others have a grace period of 2 hours

        Besides the standard frequencies, there is a one-time frequency:  `urgent`.
        The default action for `urgent` is called `trip` and it immediately sets the
        associated device's status to `FIX`; the `alert` action will also cause text
        messages and email to be sent, while the `clear` action will remove that
        particular `pulse` from `clues`, possibly changing the status to `Good`.


        ---

        [^1]: The web server is a custom server called `pulse`.  It is based on the
              `SimpleHTTPServer`, but simpler -- the `SimpleHTTPServer` is designed to
              serve files, while the `pulse` server just returns the `204`[^2] code,
              logs the request, and writes a message file.

        [^2]: `204` is the `No Content` status code, but indicates success.

        [^3]: By default, logging is sent to stderr; a command line parameter is available
              to set the name and location of the file, which will rotate at midnight.

        [^4]: By default, message files are written in the server's startup directory;
              a command line parameter is available to set the location
              (and should be used for production).
        """)
if isinstance(help_md, unicode):
    help_md = help_md.encode('utf-8')


## API

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
                print('\nts: %r\nip: %r\nfreq: %r\nname:%r' % (timestamp, ip, freq, name))
                timestamp = datetime.strptime(timestamp, '%d/%b/%Y %H:%M:%S')
                msg_file_name = timestamp.strftime('IP-%%s-%%s-%Y%m%d_%H%M%S.txt') % (ip, name, )
                print('mfn: %r' % (msg_file_name, ))
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

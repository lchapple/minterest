#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinerterest clone -- main
"""

import sys
import signal
import logging

from tornado import ioloop, httpserver, gen
from tornado.options import options, define

from api import PinterestAPI
from user import User
from pin import Pin
from userpin import UserPin
from db import init_db_connection_pool

Log = None

#
# command line paramaters
#
define('debug', default=True)
define('port', type=int, default=80, help='Port to listen on')
define('fe_path', type=str, default='./app', help='Path to front-end files e.g. index.html')
define('db_host', type=str, default='127.0.0.1', help='Database server hostname/ip')
define('db_port', type=int, default=3306, help='Database server port')
define('db_name', type=str, default='pinterest', help='Database name')
define('db_user', type=str, default='root', help='Database user')
define('db_pw', type=str, default='pinterest', help='Database password')
define('certfile', type=str, help='Path to server certificate if app should support https natively')
define('keyfile', type=str, help='Path to private key (w/o passphrase) if app should support https natively')
define('force_db_reset', type=int, default=0, help='Set to non-zero to force db tables to be rebuilt')


@gen.coroutine
def init_db():
    models = (User, Pin, UserPin)
    init_tables = options.force_db_reset != 0
    init_db_connection_pool(options.db_host, options.db_port, options.db_user, options.db_pw, options.db_name)
    if not init_tables:
        for model in models:
            exists = yield model.db_table_exists()
            if not exists:
                init_tables = True
                break
    if init_tables:
        Log.warning('Dropping all DB tables and initializing')
        for model in models:
            yield model.create_table()


def start_service():
    global Log
    options.parse_command_line()

    Log = logging.getLogger()
    if options.debug:
        Log.setLevel(logging.DEBUG)

    required_options = ('port', 'fe_path', 'db_host', 'db_port', 'db_name', 'db_user', 'db_pw')
    for opt in required_options:
        if getattr(options, opt) is None:
            Log.error('Missing {} parameter'.format(opt))
            options.print_help()
            return 2

    Log.info('Starting Pinterest clone app')
    for opt, val in options.as_dict().iteritems():
        Log.info('  {}={}'.format(opt, val))

    # enable clean shutdown via kill
    signal.signal(signal.SIGTERM, stopService)

    ioloop.IOLoop.instance().run_sync(init_db)

    service = PinterestAPI(options.fe_path, Log)
    if options.certfile and options.keyfile:
        http_server = httpserver.HTTPServer(service, ssl_options={'keyfile': options.keyfile,
                                                                  'certfile': options.certfile})
    else:
        http_server = httpserver.HTTPServer(service, xheaders=True)
    http_server.listen(options.port)

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

    stopService(signal.SIGINT, None)


def stopService(signum, frame):
    if Log:
        Log.info('Pinterest clone app shutting down')
    exit()


if __name__ == "__main__":
    sys.exit(start_service())

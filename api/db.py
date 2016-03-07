#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan DB pool
"""

from tornado import gen
from tornado_mysql import pools


DBPool = None


def init_db_connection_pool(host, port, user, pw, db):
    global DBPool
    DBPool = pools.Pool(dict(host=host, port=port, user=user, passwd=pw, db=db), max_idle_connections=1, max_recycle_sec=3600)
    DBPool.DEBUG = True


class DBBacked(object):

    @staticmethod
    def db_pool():
        return DBPool

    @classmethod
    def _table_name(cls):
        raise NotImplementedError

    @classmethod
    def _table_definition(cls):
        raise NotImplementedError

    @classmethod
    @gen.coroutine
    def db_table_exists(cls):
        cursor = yield cls.db_pool().execute("SHOW TABLES LIKE '{}'".format(cls._table_name()))
        raise gen.Return(cursor.rowcount >= 1)

    @classmethod
    @gen.coroutine
    def create_table(cls):
        yield cls.db_pool().execute("DROP TABLE IF EXISTS {}".format(cls._table_name()))
        yield cls.db_pool().execute("CREATE TABLE {} ({})".format(cls._table_name(), cls._table_definition()))

#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan User
"""

import hashlib
from tornado import gen
from db import DBBacked


class UnauthorizedError(Exception):
    pass


class User(DBBacked):

    def __init__(self, name, pw):
        super(User, self).__init__()
        self._uid = User._uid_from_name(name)
        self._name = name[:128]
        self._pw = pw[:32]
        self._stored = False

    @property
    def uid(self):
        return self._uid

    @property
    def name(self):
        return self._name

    @gen.coroutine
    def update(self, name=None, pw=None):
        if name:
            self._name = name[128]
        if pw:
            self._pw = pw[:32]
        if not self._stored:
            cursor = yield self.db_pool().execute("INSERT INTO user (uid, name, pw) VALUES (%s, %s, %s)", (self._uid, self._name, self._pw))
            if cursor.rowcount != 1:
                raise KeyError
            self._stored = True
        elif name or pw:
            cursor = yield self.db_pool().execute("UPDATE user SET name=%s,pw=%s WHERE uid=%s", (self._name, self._pw, self._uid))
            if cursor.rowcount != 1:
                raise KeyError

    @gen.coroutine
    def save(self):
        yield self.update()

    @classmethod
    @gen.coroutine
    def fetch(cls, uid):
        cursor = yield cls.db_pool().execute("SELECT uid, name, pw FROM user WHERE uid=%s", (uid,))
        if cursor.rowcount != 1:
            raise ValueError
        row = cursor.fetchone()
        user = cls(row[1], row[2])
        user._stored = True
        raise gen.Return(user)

    @classmethod
    @gen.coroutine
    def login(cls, name, pw):
        uid = User._uid_from_name(name)
        cursor = yield cls.db_pool().execute("SELECT uid, name, pw FROM user WHERE uid=%s", (uid,))
        if cursor.rowcount != 1:
            raise ValueError
        row = cursor.fetchone()
        if pw != row[2]:
            raise UnauthorizedError('User ({}) password incorrect'.format(name))
        user = cls(name, pw)
        user._stored = True
        raise gen.Return(user)

    @classmethod
    @gen.coroutine
    def exists(cls, name):
        uid = User._uid_from_name(name)
        cursor = yield cls.db_pool().execute("SELECT uid, name, pw FROM user WHERE uid=%s", (uid,))
        raise gen.Return(cursor.rowcount == 1)

    def boards(self):
        raise NotImplementedError

    @staticmethod
    def _uid_from_name(name):
        return hashlib.sha256(name).hexdigest()

    @classmethod
    def _table_name(cls):
        return 'user'

    @classmethod
    def _table_definition(cls):
        return 'uid CHAR(64) NOT NULL UNIQUE KEY, name VARCHAR(128) NOT NULL UNIQUE, pw CHAR(32) NOT NULL'

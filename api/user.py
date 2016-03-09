#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan -- User
"""

import hashlib
from tornado import gen
from db import DBBacked


class UnauthorizedError(Exception):
    pass


class User(DBBacked):

    def __init__(self, name, pw):
        super(User, self).__init__()
        self._guid = User._guid_from_name(name)
        self._name = name[:128]
        self._pw = pw[:32]
        self._stored = False

    @property
    def api_representation(self):
        return {'id': self._guid,
                'name': self.name}

    @property
    def guid(self):
        return self._guid

    @property
    def name(self):
        return self._name

    @gen.coroutine
    def update(self, name=None, pw=None):
        if name:
            self._name = name[:128]
        if pw:
            self._pw = pw[:32]
        if not self._stored:
            cursor = yield self.db_pool().execute("INSERT INTO user (id, name, pw) VALUES (%s, %s, %s)", (self._guid, self._name, self._pw))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError
            self._stored = True
        elif name or pw:
            cursor = yield self.db_pool().execute("UPDATE user SET name=%s,pw=%s WHERE id=%s", (self._name, self._pw, self._guid))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError

    @gen.coroutine
    def save(self):
        yield self.update()

    @classmethod
    @gen.coroutine
    def fetch(cls, guid):
        cursor = yield cls.db_pool().execute("SELECT id, name, pw FROM user WHERE id=%s", (guid,))
        if cursor.rowcount != 1:
            cursor.close()
            raise KeyError
        row = cursor.fetchone()
        cursor.close()
        user = cls(row[1], row[2])
        user._stored = True
        raise gen.Return(user)

    @classmethod
    @gen.coroutine
    def login(cls, name, pw):
        guid = User._guid_from_name(name)
        cursor = yield cls.db_pool().execute("SELECT id, name, pw FROM user WHERE id=%s", (guid,))
        if cursor.rowcount != 1:
            cursor.close()
            raise ValueError
        row = cursor.fetchone()
        cursor.close()
        if pw != row[2]:
            raise UnauthorizedError('User ({}) password incorrect'.format(name))
        user = cls(name, pw)
        user._stored = True
        raise gen.Return(user)

    @classmethod
    @gen.coroutine
    def exists(cls, name):
        guid = User._guid_from_name(name)
        cursor = yield cls.db_pool().execute("SELECT id FROM user WHERE id=%s", (guid,))
        exists = cursor.rowcount == 1
        cursor.close()
        raise gen.Return(exists)

    def boards(self):
        raise NotImplementedError

    @staticmethod
    def _guid_from_name(name):
        return hashlib.sha256(name).hexdigest()

    @classmethod
    def _table_name(cls):
        return 'user'

    @classmethod
    def _table_definition(cls):
        return 'id CHAR(64) NOT NULL UNIQUE KEY, name VARCHAR(128) NOT NULL UNIQUE, pw CHAR(32) NOT NULL'

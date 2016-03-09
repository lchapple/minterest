#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan -- UserPin - a User's view of a Pin
"""

from time import time
import logging
from tornado import gen
from db import DBBacked
from pin import Pin

Log = logging.getLogger()


class UserPin(DBBacked):

    def __init__(self, user_id, pin, caption, private, modified=None):
        super(UserPin, self).__init__()
        self._user_id = user_id
        self._pin = pin
        self._caption = caption.strip()[:512] if caption else None
        self._private = private
        self._modified = modified or time()
        self._stored = False

    @property
    def api_representation(self):
        rep = self._pin.api_representation
        rep.update({'caption': self._caption,
                    'private': self._private})
        return rep

    @property
    def user_guid(self):
        return self._user_id

    @property
    def pin_guid(self):
        return self._pin.guid

    @gen.coroutine
    def update(self, caption=None, private=None):
        if caption:
            self._caption = caption.strip()[:512]
        if private:
            self._private = private
        if not self._stored:
            cursor = yield self.db_pool().execute("INSERT INTO userpin (user_id, pin_id, caption, private) VALUES (%s, %s, %s, %s)", (self._user_id, self._pin.guid, self._caption, self._private))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError
            self._stored = True
        elif caption or private:
            cursor = yield self.db_pool().execute("UPDATE userpin SET caption=%s,private=%s WHERE user_id=%s AND pin_id=%s", (self._caption, self._private, self._user_id, self._pin.guid))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError

    @gen.coroutine
    def save(self):
        yield self.update()

    @classmethod
    @gen.coroutine
    def fetch(cls, user_id, pin_id):
        cursor = yield cls.db_pool().execute("SELECT caption, private, modified FROM userpin WHERE user_id=%s AND pin_id=%s", (user_id, pin_id))
        if cursor.rowcount != 1:
            cursor.close()
            raise KeyError
        row = cursor.fetchone()
        cursor.close()
        pin = yield Pin.fetch(guid=pin_id)
        userpin = cls(user_id, pin, row[0], row[1], row[2])
        userpin._stored = True
        raise gen.Return(userpin)

    @classmethod
    @gen.coroutine
    def list_for_user(cls, user_id, limit=None):
        userpins = []
        # TODO: replace this with a join, but to do that need to know internals of pin table...
        cursor = yield cls.db_pool().execute("SELECT caption, private, modified, pin_id FROM userpin WHERE user_id=%s", (user_id,))
        cursor.arraysize = min(cursor.rowcount, limit or cursor.rowcount)
        rows = cursor.fetchmany()
        for row in rows:
            pid = row[3]
            try:
                pin = yield Pin.fetch(guid=pid)
            except KeyError:
                Log.warning('Userpin record references Pin record that isn\'t in DB, user={}, pin={}'.format(user_id, pid))
                continue
            userpins.append(cls(user_id, pin, row[0], row[1], row[2]))
        raise gen.Return(userpins)

    @classmethod
    @gen.coroutine
    def exists(cls, user_id, pin_id):
        cursor = yield cls.db_pool().execute("SELECT pin_id FROM userpin WHERE user_id=%s AND pin_id=%s", (user_id, pin_id))
        exists = cursor.rowcount == 1
        cursor.close()
        raise gen.Return(exists)

    @classmethod
    @gen.coroutine
    def delete(cls, uid, pid):
        cursor = yield cls.db_pool().execute("DELETE FROM userpin WHERE user_id=%s AND pin_id=%s", (uid, pid))
        cursor.close()

    @classmethod
    def _table_name(cls):
        return 'userpin'

    @classmethod
    def _table_definition(cls):
        return 'user_id CHAR(64) NOT NULL, pin_id CHAR(64) NOT NULL, caption VARCHAR(512) DEFAULT NULL, private BOOLEAN DEFAULT 0, modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'

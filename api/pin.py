#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan -- Pin
"""

from uuid import uuid4
from tornado import gen
from db import DBBacked


class Pin(DBBacked):

    def __init__(self, content, image, title, guid=None):
        super(Pin, self).__init__()
        self._guid = guid or uuid4().hex
        self._content = content.strip()[:2000]
        self._image = image.strip()[:2000] if image else None
        self._title = title.strip()[:255] if title else None
        self._stored = False

    @property
    def api_representation(self):
        return {'id': self._guid,
                'content': self._content,
                'image': self._image,
                'title': self._title}

    @property
    def guid(self):
        return self._guid

    @gen.coroutine
    def update(self, image=None, title=None):
        if image:
            self._image = image.strip()[:2000]
        if title:
            self._title = title.strip()[:255]
        if not self._stored:
            cursor = yield self.db_pool().execute("INSERT INTO pin (id, content, image, title) VALUES (%s, %s, %s, %s)", (self._guid, self._content, self._image, self._title))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError
            self._stored = True
        elif image or title:
            cursor = yield self.db_pool().execute("UPDATE pin SET image=%s,title=%s WHERE id=%s", (self._image, self._title, self._guid))
            failed = cursor.rowcount != 1
            cursor.close()
            if failed:
                raise KeyError

    @gen.coroutine
    def save(self):
        yield self.update()

    @classmethod
    @gen.coroutine
    def fetch(cls, guid=None, content=None):
        if guid or content:
            if guid:
                # can't get mysql driver to properly format statment if make field a parameter
                cursor = yield cls.db_pool().execute("SELECT id, content, image, title FROM pin WHERE id=%s", (guid,))
            else:
                cursor = yield cls.db_pool().execute("SELECT id, content, image, title FROM pin WHERE content=%s", (content,))
            if cursor.rowcount != 1:
                cursor.close()
                raise KeyError
            row = cursor.fetchone()
            cursor.close()
            pin = cls(row[1], row[2], row[3], row[0])
            pin._stored = True
            raise gen.Return(pin)
        else:
            raise KeyError

    @classmethod
    @gen.coroutine
    def exists(cls, guid=None, content=None):
        if guid or content:
            if guid:
                # can't get mysql driver to properly format statment if make field a parameter
                cursor = yield cls.db_pool().execute("SELECT id FROM pin WHERE id='%s'", (guid,))
            else:
                cursor = yield cls.db_pool().execute("SELECT id FROM pin WHERE content='%s'", (content,))
            exists = cursor.rowcount == 1
            cursor.close()
            raise gen.Return(exists)
        else:
            raise gen.Return(False)

    @classmethod
    @gen.coroutine
    def list(cls, limit=None):
        pins = []
        cursor = yield cls.db_pool().execute("SELECT id, content, image, title FROM pin", ())
        cursor.arraysize = min(cursor.rowcount, limit or cursor.rowcount)
        rows = cursor.fetchmany()
        for row in rows:
            pin = cls(row[1], row[2], row[3], row[0])
            pin._stored = True
            pins.append(pin)
        raise gen.Return(pins)

    @classmethod
    def _table_name(cls):
        return 'pin'

    @classmethod
    def _table_definition(cls):
        return 'id CHAR(64) NOT NULL UNIQUE KEY, content VARCHAR(2000) NOT NULL, image VARCHAR(2000), title CHAR(255)'

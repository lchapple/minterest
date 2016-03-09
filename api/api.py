#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan -- REST API
"""


import json
import httplib
from tornado import web, gen
from user import User, UnauthorizedError
from pin import Pin
from userpin import UserPin


class PinterestAPI(web.Application):
    API_MAJOR_VERSION = 1
    API_MINOR_VERSION = 0

    def __init__(self, path_to_frontend, log):
        super(PinterestAPI, self).__init__([(r'/api/version$', VersionHandler),
                                            (r'/api/v1/users$', UsersHandler, {}, UsersHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)$', UserMaintenanceHandler, {}, UserMaintenanceHandler.__name__),
                                            #
                                            # skip concept of boards for the moment... and just have pins owned by user directly
                                            # (r'/api/v1/users/([^/.]+)/boards$', BoardsHandler, {}, BoardsHandler.__name__),
                                            # (r'/api/v1/users/([^/.]+)/boards/([^/.]+)$', BoardMaintenanceHandler, {}, BoardMaintenanceHandler.__name__),
                                            # (r'/api/v1/users/([^/.]+)/boards/([^/.]+)/pins$', UserPinsHandler, {}, UserPinsHandler.__name__),
                                            # (r'/api/v1/users/([^/.]+)/boards/([^/.]+)/pins/([^/.]+)$', PinMaintenanceHandler, {}, PinMaintenanceHandler.__name__),
                                            #
                                            (r'/api/v1/pins$', RawPinsHandler, {}, RawPinsHandler.__name__),
                                            (r'/api/v1/pins/([^/.]+)$', RawPinMaintenanceHandler, {}, RawPinMaintenanceHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/pins$', UserPinsHandler, {}, UserPinsHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/pins/([^/.]+)$', PinMaintenanceHandler, {}, PinMaintenanceHandler.__name__),
                                            #
                                            (r'/(.*)$', web.StaticFileHandler, {'path': path_to_frontend, 'default_filename': 'index.html'})],
                                           cookie_secret='9d007b5fa7974d9a9b41a19741eec415')
        self.log = log
        self.base_uri = None    # initialized when recieve 1st request

    def link(self, path):
        return self.base_uri + path

    def user_representation(self, user):
        rep = {'links': {'self': self.link(self.reverse_url(UserMaintenanceHandler.__name__, user.guid)),
                         'pins': self.link(self.reverse_url(UserPinsHandler.__name__, user.guid))}}
        rep.update(user.api_representation)
        return rep

    def pin_representation(self, pin):
        rep = {'links': {'self': self.link(self.reverse_url(RawPinMaintenanceHandler.__name__, pin.guid))}}
        rep.update(pin.api_representation)
        return rep

    def userpin_representation(self, userpin):
        rep = {'links': {'self': self.link(self.reverse_url(PinMaintenanceHandler.__name__, userpin.user_guid, userpin.pin_guid))}}
        rep.update(userpin.api_representation)
        return rep


#
# base handler to encapsulate common methods/info such as identity
#
class BaseHandler(web.RequestHandler):
    AUTH_COOKIE = 'user'

    def prepare(self):
        super(BaseHandler, self).prepare()
        if not self.application.base_uri:
            self.application.base_uri = '{}://{}'.format(self.request.protocol, self.request.host)

    def compute_etag(self):
        return None     # disable caching since Angular $resource doesn't deal with 304's well

    def get_current_user(self):
        return self.get_secure_cookie(self.AUTH_COOKIE)

    def set_current_user(self, guid):
        self.set_secure_cookie(self.AUTH_COOKIE, guid)

    def clear_current_user(self):
        self.clear_cookie(self.AUTH_COOKIE)


class UserResourceHandler(BaseHandler):
    def prepare(self):
        super(UserResourceHandler, self).prepare()
        # assumes first path arg in uri is the id of the resource owner
        authenticated_uid = self.get_current_user()
        if len(self.path_args) > 0 and authenticated_uid != self.path_args[0]:
            self.send_error(httplib.UNAUTHORIZED)


#
# admin endpoint handlers
#
class VersionHandler(BaseHandler):
    def get(self):
        self.write({'major': self.application.API_MAJOR_VERSION,
                    'minor': self.application.API_MINOR_VERSION,
                    'api_version': '{}.{}'.format(self.application.API_MAJOR_VERSION, self.application.API_MINOR_VERSION)})


class UsersHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        try:
            name = self.get_argument('name')
            pw = self.get_argument('pw')
            target_url = self.get_argument('next', None)
        except web.MissingArgumentError as e:
            self.application.log.info('Users GET (login) request malformed, error={}, url={}, body={}'.format(e, self.request.uri, self.request.body))
            self.send_error(httplib.BAD_REQUEST)
            return

        try:
            user = yield User.login(name, pw)
        except (ValueError, UnauthorizedError):
            self.send_error(httplib.UNAUTHORIZED)
            return

        self.set_current_user(user.guid)
        if target_url:
            self.redirect(target_url)
        else:
            self.write(self.application.user_representation(user))

    @gen.coroutine
    def post(self):
        try:
            body = json.loads(self.request.body)
            name = body['name']
            pw = body['pw']
            target_url = body.get('next')
        except (KeyError, ValueError, TypeError) as e:
            self.application.log.info('User creation request malformed, error={}, url={}, body={}'.format(e, self.request.uri, self.request.body))
            self.send_error(httplib.BAD_REQUEST)
            return

        exists = yield User.exists(name)
        if exists:
            self.send_error(httplib.CONFLICT)
            return

        user = User(name, pw)
        yield user.save()
        self.set_current_user(user.guid)
        if target_url:
            self.redirect(target_url)
        else:
            self.set_header('Location', self.reverse_url(UserMaintenanceHandler.__name__, user.guid))
            self.write(self.application.user_representation(user))
            self.set_status(httplib.CREATED)


class UserMaintenanceHandler(UserResourceHandler):
    @gen.coroutine
    def get(self, uid):
        try:
            user = yield User.fetch(uid)
        except KeyError:
            self.clear_current_user()
            self.send_error(httplib.NOT_FOUND)
            return

        self.write(self.application.user_representation(user))

    def patch(self, uid):
        raise NotImplementedError

    def delete(self, uid):
        raise NotImplementedError


class RawPinsHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        limit = self.get_argument('limit', None)
        pins = yield Pin.list(limit)
        self.write({pin.guid: self.application.pin_representation(pin) for pin in pins})


class RawPinMaintenanceHandler(BaseHandler):
    @gen.coroutine
    def get(self, pid):
        try:
            pin = yield Pin.fetch(guid=pid)
        except KeyError:
            self.send_error(httplib.NOT_FOUND)
            return
        self.write(self.application.pin_representation(pin))


class UserPinsHandler(UserResourceHandler):
    @gen.coroutine
    def get(self, uid):
        limit = self.get_argument('limit', None)
        userpins = yield UserPin.list_for_user(uid, limit)
        self.write({upin.pin_guid: self.application.userpin_representation(upin) for upin in userpins})

    @gen.coroutine
    def post(self, uid):
        try:
            body = json.loads(self.request.body)
            pid = body.get('pin_id')
            content = body.get('content')
            image = body.get('image')
            title = body.get('title')
            caption = body.get('caption')
            private = body.get('private', False)
            if pid is None and content is None:
                raise KeyError
        except (KeyError, ValueError, TypeError):
            self.send_error(httplib.BAD_REQUEST)
            return

        try:
            pin = yield Pin.fetch(guid=pid, content=content)
        except KeyError:
            if not content:
                self.send_error(httplib.NOT_FOUND)
                return
            pin = Pin(content, image, title)
            yield pin.save()

        userpin = UserPin(uid, pin, caption, private)
        yield userpin.save()
        self.write(self.application.userpin_representation(userpin))
        self.set_status(httplib.CREATED)


class PinMaintenanceHandler(UserResourceHandler):
    @gen.coroutine
    def get(self, uid, pid):
        try:
            userpin = yield UserPin.fetch(uid, pid)
        except KeyError:
            self.send_error(httplib.NOT_FOUND)
            return
        self.write(self.application.userpin_representation(userpin))

    def patch(self, uid, pid):
        raise NotImplementedError

    @gen.coroutine
    def delete(self, uid, pid):
        yield UserPin.delete(uid, pid)
        self.set_status(httplib.NO_CONTENT)

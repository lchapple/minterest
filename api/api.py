#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan REST API
"""


import httplib
from tornado import web, httputil, gen
from user import User, UnauthorizedError


class PinterestAPI(web.Application):
    API_MAJOR_VERSION = 1
    API_MINOR_VERSION = 0
    LOGIN_URL = r'/api/login'

    def __init__(self, path_to_frontend, log):
        super(PinterestAPI, self).__init__([(r'/api/version$', VersionHandler),
                                            (self.LOGIN_URL+'$', LoginHandler),
                                            (r'/api/v1/users$', UsersHandler, {}, UsersHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)$', UserMaintenanceHandler, {}, UserMaintenanceHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/boards$', BoardsHandler, {}, BoardsHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/boards/([^/.]+)$', BoardMaintenanceHandler, {}, BoardMaintenanceHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/boards/([^/.]+)/pins$', PinsHandler, {}, PinsHandler.__name__),
                                            (r'/api/v1/users/([^/.]+)/boards/([^/.]+)/pins/([^/.]+)$', PinMaintenanceHandler, {}, PinMaintenanceHandler.__name__),
                                            (r'/(.*)', web.StaticFileHandler, {'path': path_to_frontend, 'default_filename': 'index.html'})],
                                           login_url=self.LOGIN_URL,
                                           cookie_secret='9d007b5fa7974d9a9b41a19741eec415')
        self.log = log


#
# base handler to encapsulate common methods/info such as identity
#
class BaseHandler(web.RequestHandler):
    AUTH_COOKIE = 'user'

    def get_current_user(self):
        return self.get_secure_cookie(self.AUTH_COOKIE)

    def set_current_user(self, uid):
        self.set_secure_cookie(self.AUTH_COOKIE, uid)

    def clear_current_user(self):
        self.clear_cookie(self.AUTH_COOKIE)


class UserResourceHandler(BaseHandler):
    def prepare(self):
        super(UserResourceHandler, self).prepare()
        # assumes first path arg in uri is the id of the resource owner
        authenticated_uid = self.get_current_user()
        if authenticated_uid != self.path_args[0]:
            self.send_error(httplib.UNAUTHORIZED)


#
# admin endpoint handlers
#
class VersionHandler(BaseHandler):
    def get(self):
        self.write({'major': self.application.API_MAJOR_VERSION,
                    'minor': self.application.API_MINOR_VERSION,
                    'api_version': '{}.{}'.format(self.application.API_MAJOR_VERSION, self.application.API_MINOR_VERSION)})


#
#  basic login handler
#
class LoginHandler(BaseHandler):
    # TODO: remove when have login page in app and change LOGIN_URL to point to it
    def get(self):
        self.write('<html><body>'
                   '<form action="{}" method="post">'.format(self.application.LOGIN_URL) +
                   'name: <input type="text" name="name">'
                   'password: <input type="password" name="pw">'
                   '<input type="hidden" value="{}" name="next">'.format(self.get_argument('next', '')) +
                   '<input type="submit" value="Sign in">'
                   '</form>'
                   '<form action="{}" method="post">'.format(self.reverse_url(UsersHandler.__name__)) +
                   'name: <input type="text" name="name">'
                   'password: <input type="password" name="pw">'
                   '<input type="hidden" value="{}" name="next">'.format(self.get_argument('next', '')) +
                   '<input type="submit" value="Create account">'
                   '</form>'
                   '</body></html>')

    @gen.coroutine
    def post(self):
        try:
            name = self.get_argument('name')
            pw = self.get_argument('pw')
            target_url = self.get_argument('next', None)
        except web.MissingArgumentError as e:
            self.application.log.info('Login request malformed, error={}, url={}, body={}'.format(e, self.request.uri, self.request.body))
            self.send_error(httplib.BAD_REQUEST)
            return

        try:
            user = yield User.login(name, pw)
        except (ValueError, UnauthorizedError):
            # failed to login, send back to login page
            params = {'invalid': 'true'}
            if target_url:
                params.update({'next': target_url})
            self.redirect(httputil.url_concat(self.application.LOGIN_URL, params))
            return

        self.set_current_user(user.uid)
        if target_url:
            self.redirect(target_url)
        else:
            self.set_header('Location', self.reverse_url(UserMaintenanceHandler.__name__, user.uid))
            self.write({'uid': user.uid,
                        'name': user.name,
                        'boards': self.reverse_url(BoardsHandler.__name__, user.uid)})



class UsersHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        try:
            name = self.get_argument('name')
            pw = self.get_argument('pw')
            target_url = self.get_argument('next', None)
        except web.MissingArgumentError as e:
            self.application.log.info('User creation request malformed, error={}, url={}, body={}'.format(e, self.request.uri, self.request.body))
            self.send_error(httplib.BAD_REQUEST)
            return

        exists = yield User.exists(name)
        if exists:
            self.redirect(httputil.url_concat(self.application.LOGIN_URL, {'next': target_url} if target_url else {}))
            return

        user = User(name, pw)
        yield user.save()
        self.set_current_user(user.uid)
        if target_url:
            self.redirect(target_url)
        else:
            self.set_header('Location', self.reverse_url(UserMaintenanceHandler.__name__, user.uid))
            self.write({'uid': user.uid,
                        'name': user.name,
                        'boards': self.reverse_url(BoardsHandler.__name__, user.uid)})


class UserMaintenanceHandler(UserResourceHandler):

    @web.authenticated
    @gen.coroutine
    def get(self, uid):
        try:
            user = yield User.fetch(uid)
        except KeyError:
            self.clear_current_user()
            self.send_error(httplib.NOT_FOUND)
            return

        self.write({'uid': uid,
                    'name': user.name,
                    'boards': self.reverse_url(BoardsHandler.__name__, uid)})

    def patch(self, uid):
        raise NotImplementedError

    def delete(self, uid):
        raise NotImplementedError


class BoardsHandler(UserResourceHandler):
    def get(self, uid):
        raise NotImplementedError

    def post(self, uid):
        raise NotImplementedError


class BoardMaintenanceHandler(UserResourceHandler):
    def get(self, uid, bid):
        raise NotImplementedError

    def patch(self, uid, bid):
        raise NotImplementedError

    def delete(self, uid, bid):
        raise NotImplementedError


class PinsHandler(UserResourceHandler):
    def get(self, uid, bid):
        raise NotImplementedError

    def post(self, uid, bid):
        raise NotImplementedError


class PinMaintenanceHandler(UserResourceHandler):
    def get(self, uid, bid, pid):
        raise NotImplementedError

    def patch(self, uid, bid, pid):
        raise NotImplementedError

    def delete(self, uid, bid, pid):
        raise NotImplementedError

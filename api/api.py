#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2016 Loren Chapple
#
"""
Pinterest cloan -- REST API
"""


from flask import Flask, jsonify, request, session, abort, current_app, url_for
from flask.ext.sqlalchemy import SQLAlchemy
import httplib


app = Flask(__name__, static_folder='../app', static_url_path='')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '834282ec30804df7b1505253c3e8390c'
db = SQLAlchemy(app)


API_MAJOR_VERSION = 1
API_MINOR_VERSION = 0


def user_representation(user):
    rep = {'links': {'self': url_for(get_user, uid=user.id, external=True),
                     'pins': url_for(get_user_pins, uid=user.id)}}
    rep.update(user.api_representation)
    return rep


def pin_representation(pin):
    rep = {'links': {'self': url_for(get_pin, pid=pin.id)}}
    rep.update(pin.api_representation)
    return rep


def userpin_representation(userpin):
    rep = {'links': {'self': url_for(get_user_pin, uid=userpin.user_id, pid=userpin.pin_id)}}
    rep.update(userpin.api_representation)
    return rep


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/version', methods=['GET'])
def version():
    return jsonify({'major': API_MAJOR_VERSION,
                    'minor': API_MINOR_VERSION,
                    'api_version': '{}.{}'.format(API_MAJOR_VERSION, API_MINOR_VERSION)})


@app.route('/api/v1/users', methods=['GET'])
def login():
    try:
        name = request.values['name']
        pw = request.values['pw']
    except KeyError as e:
        current_app.log.info('Users GET (login) request malformed, error={}, url={}, body={}'.format(e, request.url, request.data))
        abort(httplib.BAD_REQUEST)
        return

    user = User.query.filter_by(name=name, pw=pw).first_or_404()
    session['user'] = user
    return jsonify(user_representation(user))


@app.route('/api/v1/users', methods=['POST'])
def create_account():
    try:
        body = request.get_json()
        name = body['name']
        pw = body['pw']
    except (KeyError, ValueError, TypeError) as e:
        current_app.log.info('User creation request malformed, error={}, url={}, body={}'.format(e, request.url, request.data))
        abort(httplib.BAD_REQUEST)
        return

    user = User.query.filter_by(name=name, pw=pw).first()
    if user:
        abort(httplib.CONFLICT)
        return

    user = User(name=name, pw=pw)
    db.session.add(user)
    session['user'] = user
    return jsonify(user_representation(user)), httplib.CREATED


@app.route('/api/v1/users/<uid>', methods=['GET'])
def get_user(uid):
    user = User.query.filter_by(id=uid).first_or_404()
    return jsonify(user_representation(user))


@app.route('/api/v1/users/<uid>', methods=['PATCH'])
def patch_user(uid):
    raise NotImplementedError


@app.route('/api/v1/users/<uid>', methods=['DELETE'])
def delete_user(uid):
    raise NotImplementedError


@app.route('/api/v1/pins', methods=['GET'])
def get_all_pins():
    query = Pin.query
    limit = request.values.get('limit')
    if limit:
        query = query.limit(limit)
    pins = query.all()
    return jsonify({pin.id: pin_representation(pin) for pin in pins})


@app.route('/api/v1/pins/<pid>', methods=['GET'])
def get_pin(pid):
    pin = Pin.query.filter_by(id=pid).first_or_404()
    return jsonify(pin_representation(pin))


@app.route('/api/v1/users/<uid>/pins', methods=['GET'])
def get_user_pins(uid):
    query = UserPin.query.filter_by(user_id=uid)
    limit = request.values.get('limit')
    if limit:
        query = query.limit(limit)
    userpins = query.all()
    return jsonify({upin.pin_id: userpin_representation(upin) for upin in userpins})


@app.route('/api/v1/users/<uid>/pins', methods=['POST'])
def add_user_pin(uid):
    try:
        body = request.get_json()
        pid = body.get('pin_id')
        content = body.get('content')
        image = body.get('image')
        title = body.get('title')
        caption = body.get('caption')
        private = body.get('private', False)
        if pid is None and content is None:
            raise KeyError
    except (KeyError, ValueError, TypeError):
        abort(httplib.BAD_REQUEST)
        return

    criteria = dict(id=pid) if pid else dict(content=content)
    pin = Pin.query.filter_by(**criteria).first()
    if not pin:
        if not content:
            abort(httplib.NOT_FOUND)
            return
        pin = Pin(content=content, image=image, title=title)
        db.session.add(pin)

    userpin = UserPin(user_id=uid, pin_id=pin.id, caption=caption, private=private)
    db.session.add(userpin)
    return jsonify(userpin_representation(userpin)), httplib.CREATED


@app.route('/api/v1/users/<uid>/pins/<pid>', methods=['GET'])
def get_user_pin(uid, pid):
    userpin = UserPin.query.filter_by(user_id=uid, pin_id=pid).first_or_404()
    return jsonify(userpin_representation(userpin))


@app.route('/api/v1/users/<uid>/pins/<pid>', methods=['PATCH'])
def patch_user_pin(uid, pid):
    raise NotImplementedError


@app.route('/api/v1/users/<uid>/pins/<pid>', methods=['DELETE'])
def delete_user_pin(uid, pid):
    upin = UserPin.query.filter_by(user_id=uid, pin_id=pid).first_or_404()
    db.session.delete(upin)
    return '', httplib.NO_CONTENT


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    pw = db.Column(db.String(32), nullable=False)

    @property
    def api_representation(self):
        return {'id': self.id,
                'name': self.name}


class Pin(db.Model):
    __tablename__ = 'pin'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(2000), unique=False, nullable=False)
    image = db.Column(db.String(2000), nullable=True)
    title = db.Column(db.Unicode(255), nullable=True)

    @property
    def api_representation(self):
        return {'id': self.id,
                'content': self.content,
                'image': self.image,
                'title': self.title}


# TODO: replace this association table with many to many relationship between User and Pin
class UserPin(db.Model):
    __tablename__ = 'userpin'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pin_id = db.Column(db.Integer, db.ForeignKey('pin.id'))
    caption = db.Column(db.String(512), nullable=True, default=None)
    private = db.Column(db.Boolean, nullable=False, default=False)
    modified = db.Column(db.DateTime, nullable=False)

    @property
    def api_representation(self):
        rep = self._pin.api_representation
        rep.update({'caption': self.caption,
                    'private': self.private})
        return rep


if __name__ == "__main__":
    db.create_all()
    app.run(port=8080, debug=True)

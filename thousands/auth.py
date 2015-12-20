# coding: utf8
import json
import httplib2
import urllib
import logging

from flask.ext.login import login_user
from flask import (request, g, redirect,
                   url_for, abort, render_template, flash)
from oauth2client.client import FlowExchangeError, OAuth2WebServerFlow

import dao

from thousands import app

VK_API_VERSION = "5.37"


class AuthError(Exception):
    pass


def vk_flow(state):
    return OAuth2WebServerFlow(
        app.config['VK_CLIENT_ID'],
        client_secret=app.config['VK_CLIENT_SECRET'],
        scope='',
        redirect_uri='http://1000.southural.ru/login/vk',
        auth_uri='https://oauth.vk.com/authorize',
        token_uri='https://oauth.vk.com/access_token',
        revoke_uri=None,
        device_uri=None,
        state=state,
        v=VK_API_VERSION)


def su_flow(state):
    return OAuth2WebServerFlow(
        app.config['SU_CLIENT_ID'],
        client_secret=app.config['SU_CLIENT_SECRET'],
        scope='openid profile',
        redirect_uri='http://1000.southural.ru/login/su',
        auth_uri='http://www.southural.ru/oauth2/authorize',
        token_uri='http://www.southural.ru/oauth2/token',
        revoke_uri=None,
        device_uri=None,
        state=state)


@app.route('/login')
def login_form():
    redirect = request.args.get('r')
    return render_template('/login.html',
                           vk_flow=vk_flow(redirect),
                           su_flow=su_flow(redirect))


@app.route('/login/su')
def su_login():
    return oauth_login(request, su_flow('state'), su_get_user)


@app.route('/login/vk')
def vk_login():
    return oauth_login(request, vk_flow('state'), vk_get_user)


@app.route('/login/as/<int:user_id>')
def login_as(user_id):
    if app.config['DEBUG']:
        user = g.users_dao.get_by_id(unicode(user_id))
        if user is None:
            abort(404)
        login_user(user)
        return redirect(url_for('user', user_id=user_id))
    else:
        abort(404)


def oauth_login(req, flow, get_user):
    if 'error' in req.args.keys():
        raise AuthError(req.args.get('error_description'))

    try:
        credentials = flow.step2_exchange(req.args.get('code'))
    except FlowExchangeError, e:
        raise AuthError('Error getting access token', e)

    user, created = get_user(credentials)
    if user is not None:
        login_user(user)
        if created:
            app.logger.info("New user registration uid=%s, src=%s, name=%s",
                            user.get_id(),
                            user.src,
                            user.name)
            flash(u'Регистрация завершена')
            return redirect(url_for('user', user_id=user.get_id()))
        else:
            return redirect(req.args.get('state'))

    abort(401)


def vk_get_user(credentials):
    user = g.users_dao.get(unicode(credentials.token_response['user_id']),
                           dao.AUTH_SRC_VK)
    if user is not None:
        return user, False

    conn = httplib2.Http()
    credentials.authorize(conn)
    params = {
        'v': '5.37',
        'lang': 'ru',
        'user_ids': credentials.token_response['user_id'],
        'fields': 'photo_50, photo_200_orig, city'}

    resp, content = conn.request('https://api.vk.com/method/users.get',
                                 'POST',
                                 urllib.urlencode(params))

    if resp.status != 200:
        logging.error("Error getting user profile from vk api: %d",
                      resp.status)
        logging.error(content)
        return None

    data = json.loads(content)['response'][0]
    if 'error' in data:
        logging.error("Error getting profile data")
        logging.error(data['error'])
        return None

    user = dao.User()
    user.oauth_id = unicode(credentials.token_response['user_id'])
    user.name = u"{} {}".format(
        data.get('first_name', ''),
        data.get('last_name', ''))
    user.src = dao.AUTH_SRC_VK

    fd = urllib.urlopen(data['photo_200_orig'])
    if fd.getcode() == 200:
        user.image_id = g.images_dao.create(fd.read(), fd.info().gettype())
    else:
        user.image_id = None

    fd = urllib.urlopen(data['photo_50'])
    if fd.getcode() == 200:
        user.preview_id = g.images_dao.create(fd.read(), fd.info().gettype())
    else:
        user.preview_id = None

    user.id = g.users_dao.create(user)

    return user, True


def su_get_user(credentials):
    conn = httplib2.Http()
    credentials.authorize(conn)
    resp, content = conn.request('http://www.southural.ru/oauth2/UserInfo',
                                 'POST')
    if resp.status != 200:
        logging.error("Error getting user profile from su api: %d",
                      resp.status)
        logging.error(content)
        return None
    data = json.loads(content)
    if 'error' in data:
        logging.error("Error getting user data from su")
        logging.error(data['error'])
        return None

    user = g.users_dao.get(data['sub'], dao.AUTH_SRC_SU)
    if user is not None:
        return user, False
    user = dao.User()
    user.oauth_id = data['sub']
    user.name = data['name']
    user.src = dao.AUTH_SRC_SU
    user.image_id = None
    user.preview_id = None
    user.id = g.users_dao.create(user)

    return user, True

# coding: utf8
import urlparse
import json
import httplib2
import hashlib
from urllib import urlencode
from urllib2 import urlopen

from flask.ext.login import login_user
from flask import (request, g, redirect,
                   url_for, abort, render_template, flash)
from oauth2client.client import FlowExchangeError, OAuth2WebServerFlow

import dao

from thousands import app

VK_API_VERSION = "5.37"


class AuthError(Exception):
    pass


def vk_flow(state, redirect_root):
    return OAuth2WebServerFlow(
        app.config['VK_CLIENT_ID'],
        client_secret=app.config['VK_CLIENT_SECRET'],
        scope='',
        redirect_uri=urlparse.urljoin(redirect_root, '/login/vk'),
        auth_uri='https://oauth.vk.com/authorize',
        token_uri='https://oauth.vk.com/access_token',
        revoke_uri=None,
        device_uri=None,
        state=state,
        v=VK_API_VERSION)


def su_flow(state, redirect_root):
    return OAuth2WebServerFlow(
        app.config['SU_CLIENT_ID'],
        client_secret=app.config['SU_CLIENT_SECRET'],
        scope='openid profile',
        redirect_uri=urlparse.urljoin(redirect_root, '/login/su'),
        auth_uri='http://www.southural.ru/oauth2/authorize',
        token_uri='http://www.southural.ru/oauth2/token',
        revoke_uri=None,
        device_uri=None,
        state=state)


@app.route('/login')
def login_form():
    state = request.args.get('r')
    return render_template('/login.html',
                           vk_flow=vk_flow(state, request.url_root),
                           su_flow=su_flow(state, request.url_root))


@app.route('/login/su')
def su_login():
    return oauth_login(request,
                       su_flow('state', request.url_root),
                       su_get_user)


@app.route('/login/vk')
def vk_login():
    return oauth_login(request,
                       vk_flow('state', request.url_root),
                       vk_get_user)


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
        app.logger.warning("Error during oauth process: %s (%s)",
                           req.args.get('error'),
                           req.args.get('error_description'))
        flash(u'Невозможно выполнить вход. Повторите попытку позже',
              'error')
        return redirect(req.args.get('state'))

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


def vk_get_image(url, images_dao):
    try:
        fd = urlopen(url, timeout=2)
        if fd.getcode() == 200:
            data = fd.read()
            name = hashlib.sha1(data).hexdigest() + \
                mimetypes.guess_extension(fd.info().gettype())
            return images_dao.create(name, data)
        else:
            return None
    except IOError:
        app.logger.exception("Failed to get image from vk: %s", url)
        return None


def vk_get_user(credentials):
    user = g.users_dao.get(unicode(credentials.token_response['user_id']),
                           dao.AUTH_SRC_VK)
    if user is not None:
        return user, False

    app.logger.debug("Fetching user profile from vk.com")
    conn = httplib2.Http()
    credentials.authorize(conn)
    params = {
        'v': '5.37',
        'lang': 'ru',
        'user_ids': credentials.token_response['user_id'],
        'fields': 'photo_50, photo_200_orig, city'}

    resp, content = conn.request('https://api.vk.com/method/users.get',
                                 'POST',
                                 urlencode(params))

    if resp.status != 200:
        app.logger.error("Error getting user profile from vk api: %d, %s",
                         resp.status, content)
        return None

    data = json.loads(content)['response'][0]
    if 'error' in data:
        app.logger.error("Error getting profile data: %s", data['error'])
        return None

    app.logger.debug("Storing user in database")
    user = dao.User()
    user.oauth_id = unicode(credentials.token_response['user_id'])
    user.name = u"{} {}".format(
        data.get('first_name', ''),
        data.get('last_name', ''))
    user.src = dao.AUTH_SRC_VK

    user.image_id = vk_get_image(data['photo_200_orig'],
                                 g.images_dao)
    user.preview_id = vk_get_image(data['photo_50'],
                                   g.images_dao)

    user.id = g.users_dao.create(user)

    return user, True


def su_get_user(credentials):
    conn = httplib2.Http()
    credentials.authorize(conn)
    resp, content = conn.request('http://www.southural.ru/oauth2/UserInfo',
                                 'POST')
    if resp.status != 200:
        app.logger.error("Error getting user profile from su api: %d, %s",
                         resp.status, content)
        return None
    data = json.loads(content)
    if 'error' in data:
        app.logger.error("Error getting user data from su: %s", data['error'])
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

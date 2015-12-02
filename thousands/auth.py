import json
import httplib2
import urllib
import logging

from flask.ext.login import login_user, UserMixin
from flask import (request, g, redirect, make_response,
                   url_for, abort, render_template)
from oauth2client.client import FlowExchangeError, OAuth2WebServerFlow

from thousands import app

VK_API_VERSION = "5.37"
AUTH_SRC_VK = 1
AUTH_SRC_SU = 2


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
    redirect = request.args.get('r', url_for('profile'))
    return render_template('/login.html',
                           vk_flow=vk_flow(redirect),
                           su_flow=su_flow(redirect))


@app.route('/login/su')
def su_login():
    return oauth_login(request, su_flow('state'), su_get_user)


@app.route('/login/vk')
def vk_login():
    return oauth_login(request, vk_flow('state'), vk_get_user)


@app.route('/login/as/<user_id>')
def login_as(user_id):
    if app.config['TESTING']:
        user = g.users_dao.get_by_id(unicode(user_id))
        if user is None:
            abort(404)
        login_user(user, False, True)
        return redirect('/user/' + str(user.id))
    else:
        abort(404)


def oauth_login(req, flow, get_user):
    if 'error' in request.args.keys():
        return make_response(req.args.get('error_description'))

    try:
        credentials = flow.step2_exchange(req.args.get('code'))
    except FlowExchangeError, e:
        logging.exception(e)
        return make_response('Error getting access token')

    user, created = get_user(credentials)
    if user is not None:
        login_user(user)
        redirect_to = url_for('profile') if created else req.args.get('state')
        return redirect(redirect_to)

    abort(401)


def vk_get_user(credentials):
    user = g.users_dao.get(unicode(credentials.token_response['user_id']),
                           AUTH_SRC_VK)
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

    user = UserMixin()
    user.oauth_id = unicode(credentials.token_response['user_id'])
    user.name = u"{} {}".format(
        data.get('first_name', ''),
        data.get('last_name', ''))
    user.src = AUTH_SRC_VK

    if 'city' in data:
        user.location = data['city']['title']
    else:
        user.location = None

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

    user = g.users_dao.get(data['sub'], AUTH_SRC_SU)
    if user is not None:
        return user, False
    user = UserMixin()
    user.oauth_id = data['sub']
    user.name = data['name']
    user.src = AUTH_SRC_SU
    user.location = data.get('city', None)
    user.image_id = None
    user.preview_id = None
    user.id = g.users_dao.create(user)

    return user, True

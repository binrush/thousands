# coding: utf8
from urllib2 import urlopen, HTTPError, URLError

import functools
import mimetypes

from flask_oauthlib.client import OAuth, OAuthException
from flask_login import login_user
from flask import (request, g, redirect, session,
                   url_for, abort, render_template, flash)

from thousands import model
from thousands import app


VK_API_VERSION = "5.37"


class AuthException(Exception):
    pass

@app.errorhandler(OAuthException)
def oauth_error(error):
    app.logger.exception("Oauth error: type=%s, data=%s",
                         error.type, error.data)
    abort(500)


@app.errorhandler(AuthException)
def oauth_error(error):
    app.logger.exception("Authentication error")
    abort(401)


oauth = OAuth()


def tokengetter(key, token=None):
    return session.get(key)


vk = oauth.remote_app(
    'vk',
    base_url='https://api.vk.com/method/',
    request_token_url=None,
    access_token_url='https://oauth.vk.com/access_token',
    authorize_url='https://oauth.vk.com/authorize',
    consumer_key=app.config['VK_CLIENT_ID'],
    consumer_secret=app.config['VK_CLIENT_SECRET'],
    request_token_params={'scope': ''}
)

su = oauth.remote_app(
    'su',
    base_url='http://www.southural.ru/oauth2/',
    request_token_url=None,
    access_token_url='http://www.southural.ru/oauth2/token',
    authorize_url='http://www.southural.ru/oauth2/authorize',
    consumer_key=app.config['SU_CLIENT_ID'],
    consumer_secret=app.config['SU_CLIENT_SECRET'],
    request_token_params={'scope': 'openid profile'}
)

for ra in oauth.remote_apps.values():
    ra.tokengetter(functools.partial(tokengetter, ra.name + '_token'))


@app.route('/login')
def login_form():
    return render_template('/login.html', next=request.args.get('next'))


@app.route('/login/<any(vk, su):ra>')
def login(ra):
    return oauth.remote_apps[ra].authorize(
        callback=url_for(
            'authorized',
            ra=ra,
            next=request.args.get('next') or request.referrer or None,
            _external=True
        )
    )


@app.route('/login/<any(vk, su):ra>/authorized')
def authorized(ra):
    next_url = request.args.get('next') or url_for('index')
    resp = oauth.remote_apps[ra].authorized_response()
    if resp is None:
        app.logger.warning("User denied our request")
        flash(u'Невозможно выполнить вход. Повторите попытку позже', 'error')
        return redirect(next_url)

    session[ra + '_token'] = (resp['access_token'], None)

    user, created = get_user(resp['user_id'], ra)
    login_user(user)
    if created:
        app.logger.info("New user registration uid=%s, src=%s, name=%s",
                        user.get_id(),
                        user.src,
                        user.name)
        flash(u'Регистрация завершена')
        return redirect(url_for('user', user_id=user.get_id()))
    else:
        return redirect(next_url)


@app.route('/login/as/<int:user_id>')
def login_as(user_id):
    if app.config['DEBUG']:
        user = g.users_dao.get_by_id(unicode(user_id))
        if user is None:
            abort(404)
        login_user(user)
        return redirect(url_for('user', user_id=user_id))

    abort(404)


def get_user(user_id, ra):
    user = g.users_dao.get(unicode(user_id), model.AUTH_SRC_VK)
    if user is not None:
        return user, False

    fetch_user = vk_fetch_user if ra == 'vk' else su_fetch_user
    user, image = fetch_user(user_id)
    if image is not None:
        full, preview = image
        g.images_dao.create(full)
        g.images_dao.create(preview)
        user.image = full.name
        user.preview = preview.name
    else:
        user.image = None
        user.preview = None
    user.id = g.users_dao.create(user)
    return user, True


def check_get(ra, url, params):
    resp = ra.get(url, data=params)
    if resp.status != 200:
        raise AuthException("Error getting user profile from {} api: {:d}, {}"
                            .format(ra.name, resp.status, resp.data))
    return resp


def vk_fetch_image(url):
    fd = urlopen(url, timeout=2)
    if fd.getcode() == 200:
        image = model.Image.fromfd(
            fd,
            mimetypes.guess_extension(fd.info().gettype()))
        return image
    else:
        raise HTTPError(
            fd.getcode(), url,
            "non-200 code returned when fetching image from vk",
            {}, None)


def vk_fetch_user(user_id):
    app.logger.debug("Fetching user profile from vk.com")
    params = {
        'v': '5.37',
        'lang': 'ru',
        'user_ids': user_id,
        'fields': 'photo_50, photo_200_orig, has_photo'}

    resp = check_get(vk, 'users.get', params)

    data = resp.data['response'][0]

    if 'error' in data:
        raise AuthException("Error getting profile data: {}"
                            .format(data['error']))

    user = model.User()
    user.oauth_id = unicode(user_id)
    user.name = u"{} {}".format(
        data.get('first_name', ''),
        data.get('last_name', ''))
    user.src = model.AUTH_SRC_VK

    images = None
    if data['has_photo']:
        try:
            images = (vk_fetch_image(data['photo_200_orig']),
                      vk_fetch_image(data['photo_50']))
        except URLError:
            app.logger.exception("Failed to fetch images from vk")

    return user, images


def su_fetch_user(user_id):
    resp = check_get(su, 'UserInfo', None)
    if 'error' in resp.data:
        raise AuthException("Error getting user profile from su api: {:d}, {}"
                            .format(resp.status, resp.data))

    user = model.User()
    user.oauth_id = resp.data['sub']
    user.name = resp.data['name']
    user.src = model.AUTH_SRC_SU

    return user, None

import json, httplib2, urllib, logging

from flask.ext.login import login_user, logout_user, current_user, UserMixin
from flask import request, g, redirect, make_response, url_for, abort
from oauth2client.client import FlowExchangeError

from thousands import app

httplib2.debuglevel = 4

AUTH_SRC_VK = 1

@app.route('/login/su')
def su_login():
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))

    try:
        credentials = g.su_flow.step2_exchange(request.args.get('code'))
    except FlowExchangeError, e:
        logging.exception(e)
        return make_response('Error getting access token')
    
    conn = httplib2.Http()
    credentials.authorize(conn)
    resp, content = conn.request('http://www.southural.ru/oauth2/UserInfo', 'POST')
    return make_response(content)

@app.route('/login/vk')
def vk_login():
    return oauth_login(request, g.vk_flow, vk_get_user)

def oauth_login(req, flow, get_user):
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))
    
    try:
        credentials = flow.step2_exchange(request.args.get('code'))
    except FlowExchangeError, e:
        logging.exception(e)
        return make_response('Error getting access token')

    user = get_user(credentials)
    if user is not None:
        login_user(user)
        return redirect(url_for('profile'))

    abort(401)
   
def vk_get_user(credentials):
    user = g.users_dao.get(credentials.token_response['user_id'], AUTH_SRC_VK)
    if user is not None:
        return user

    conn = httplib2.Http()
    credentials.authorize(conn)
    params = {
            'user_ids'    : credentials.token_response['user_id'],
            'fields'      : 'photo_100'
            }
    resp, content = conn.request('https://api.vk.com/method/users.get', 'POST', urllib.urlencode(params))

    if resp.status != 200:
        logging.error("Error getting user profile from vk api: %d", resp.status)
        logging.error(content)
        return None

    data = json.loads(content)['response'][0]
    if 'error' in data:
        logging.error("Error getting profile data")
        logging.error(data['error'])
        return None
    
    user = UserMixin()
    user.oauth_id = credentials.token_response['user_id']
    user.name = u"{} {}".format(data['first_name'], data['last_name'])
    user.src = AUTH_SRC_VK
    user.email = credentials.token_response.get('email', None)
        
    fd = urllib.urlopen(data['photo_100'])
    if fd.getcode() == 200:
        user.img_id = g.images_dao.create(fd.read(), fd.info().gettype())
    else:
        user.img_id = None

    user.id = g.users_dao.create(user)

    return user

def su_get_user(credentials):

    conn = httplib2.Http()
    credentials.authorize(conn)
    resp, content = conn.request('https://www.southural.ru', 'POST')
    if resp.status != 200:
        logging.error("Error getting user profile from vk api: %d", resp.status)
        logging.error(content)
        return None
    data = json.loads(content)
    if 'error' in data:
        logging.error(data['error'])
        return None
    profile = {}
    profile['name'] = data['name']
    profile['image'] = data['photo_100']
    return profile

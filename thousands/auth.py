import json, httplib2, urllib, logging

from flask.ext.login import login_user, logout_user, current_user, UserMixin
from flask import request, g, redirect, make_response, url_for
from oauth2client.client import FlowExchangeError

from thousands import app

httplib2.debuglevel = 4

@app.route('/login/su')
def su_login():
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))

    try:
        credentials = g.su_flow.step2_exchange(request.args.get('code'))
    except FlowExchangeError, e:
        logging.exception(e)
        return make_response('Error getting access token')
    
    print credentials.token_response
    conn = httplib2.Http()
    credentials.authorize(conn)
    resp, content = conn.request('http://www.southural.ru/oauth2/UserInfo', 'POST')
    print resp
    print content
    return make_response('')

@app.route('/login/vk')
def vk_login():
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))
    
    try:
        credentials = g.vk_flow.step2_exchange(request.args.get('code'))
    except FlowExchangeError, e:
        logging.exception(e)
        return make_response('Error getting access token')

    # TODO remove magic number
    user = g.users_dao.get(credentials.token_response['user_id'], 1)
    if user is None:
        profile = vk_get_profile(credentials)
        user = UserMixin()
        user.oauth_id = credentials.token_response['user_id']
        user.name = profile['name']
        user.src = 1
        user.email = credentials.token_response.get('email', None)
        
        fd = urllib.urlopen(profile['image'])
        if fd.getcode() == 200:
            img_id = g.images_dao.create(fd.read(), fd.info().gettype())
        else:
            img_id = None

        user.img_id = img_id
        user.id = g.users_dao.create(user)

    login_user(user)
    return redirect(url_for('profile'))


def vk_get_profile(credentials):

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
        logging.error(data['error'])
        return None
    profile = {}
    profile['name'] = u"{} {}".format(data['first_name'], data['last_name'])
    profile['image'] = data['photo_100']
    return profile

def su_get_profile(credentials):

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

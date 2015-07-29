from urllib import urlencode
import json, httplib
from flask.ext.login import UserMixin
import logging


def vk_get_profile(oauth_id, at):
    conn = httplib.HTTPSConnection('api.vk.com')
    params = {
            'access_token': at,
            'user_ids'    : oauth_id,
            'fields'      : 'photo_100'
            }
    conn.request('GET', '/method/users.get?' + urlencode(params))
    response = conn.getresponse()
    if response.status != httplib.OK:
        raise
    data = json.loads(response.read())['response'][0]
    print data
    if 'error' in data:
        raise
    profile = {}
    profile['oauth_id'] = oauth_id
    profile['name'] = u"{} {}".format(data['first_name'], data['last_name'])
    profile['image'] = data['photo_100']
    return profile


def vk_get_access_token(params):
    conn = httplib.HTTPSConnection('oauth.vk.com')
    #conn.set_debuglevel(5)

    conn.request('GET', '/access_token?' + urlencode(params))
    response = json.loads(conn.getresponse().read())
    if 'error' in response:
        logging.warning("Error getting access token: %s", response['error'])
        return None
    
    email = response['email'] if 'email' in response else None

    return response['user_id'], email, response['access_token']

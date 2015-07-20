from urllib import urlencode
import json, httplib

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



from bottle import get, request, redirect
from urllib import urlencode
import json, httplib
import users, const

@get('/vk_login')
def vk_login():
    if 'error' in request.query.keys():
        return request.query['error_description']

    code = request.query['code']
    conn = httplib.HTTPSConnection('oauth.vk.com')
    #conn.set_debuglevel(5)
    params = {
            'client_id'    : request.app.config['su1000.vk_client_id'],
            'client_secret': request.app.config['su1000.vk_client_secret'],
            'code'         : code,
            'redirect_uri' : '%s://%s/vk_login' % (
                request.urlparts[0],
                request.urlparts[1]
            )
    }

    conn.request('GET', '/access_token?' + urlencode(params))
    response = json.loads(conn.getresponse().read())
    if 'error' in response:
        return response['error_description']
    
    s = request.environ.get('beaker.session')
    oauth_id = response['user_id']
    user = users.get(oauth_id, const.AUTH_SRC_VK)

    if user is None:
        at = response['access_token']
        user = vk_get_profile(oauth_id, at)
        user['email'] = response['email'] if 'email' in response else None
        s['registering_user'] = user
        s.save()
        redirect("/register", 302)
    else:
        s['user'] = user
        s.save()
        redirect("/", 302)

    return response
#            'https:///access_token?'\
#            'client_id=%s&client_secret=%s&code=%s&'\
#            'redirect_uri=%s:%s/vk_login' % (
#                request.app.config['vk_client_id'],
#                request.app.config['vk_client_secret'],
#                request.urlparts[0],
#                request.urlparts[1]))
#    conn.

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
    user = {}
    user['oauth_id'] = oauth_id
    user['src'] = const.AUTH_SRC_VK
    user['name'] = u"{} {}".format(data['first_name'], data['last_name'])
    user['image'] = data['photo_100']
    return user



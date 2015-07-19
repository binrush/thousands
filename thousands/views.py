from thousands import app
from flask import render_template, g, jsonify
import dao

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/')
def map():
    return render_template('map.html')

@app.route('/api/summits')
def summits_get():
    return jsonify(g.summits_dao.get_all())

@app.route('/vk_login')
def vk_login():
    if 'error' in request.args.keys():
        return request.query['error_description']

    code = request.args.get('code')
    conn = httplib.HTTPSConnection('oauth.vk.com')
    #conn.set_debuglevel(5)
    params = {
            'client_id'    : app.config['VK_CLIENT_ID'],
            'client_secret': app.config['VK_CLIENT_SECRET'],
            'code'         : code,
            'redirect_uri' : request.url_root + 'vk_login'
    }

    conn.request('GET', '/access_token?' + urlencode(params))
    response = json.loads(conn.getresponse().read())
    if 'error' in response:
        return response['error_description']
    
    #s = request.environ.get('beaker.session')
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


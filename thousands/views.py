from thousands import app
from flask import request, render_template, g, jsonify, redirect, url_for
from flask.ext.login import login_user, logout_user, current_user
import dao, auth
import httplib, json
from urllib import urlencode

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/')
def map():
    return render_template('map.html')

@app.route('/table')
def table():
    return render_template('table.html')

@app.route('/api/summits')
def summits_get():
    return jsonify(g.summits_dao.get_all(request.args.has_key('orderByHeight')))

@app.route('/register')
def register():
    return make_response(None)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('map'))

@app.route('/vk_login')
def vk_login():
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))

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
    
    oauth_id = response['user_id']
    # TODO remove magic number
    user = g.users_dao.get(oauth_id, 1)

    if user is None:
        at = response['access_token']
        profile = auth.vk_get_profile(oauth_id, at)
        profile['email'] = response['email'] if 'email' in response else None

        return render_template('register.html', registering_user=profile)
    else:
        login_user(user)
        return redirect(url_for('map'))


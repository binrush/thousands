from thousands import app
from flask import request, render_template, g, jsonify, redirect, url_for, session, make_response, abort
from flask.ext.login import login_user, logout_user, current_user, UserMixin
import dao, auth, forms
import httplib, json, urllib

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/')
def map():
    return render_template('map.html')

@app.route('/table')
def table():
    return render_template('table.html')

@app.route('/summit/<int:summit_id>')
def summit(summit_id):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    return render_template('summit.html', summit=s)

@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    f = forms.SummitForm(request.form)
    f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    if request.method == 'POST' and f.validate():
        summit = Summit()
        return redirect(url_for('summit', g.summits_dao.create(summit)))
    return render_template('summit_edit.html', form=f)

@app.route('/summit/edit/<int:summit_id>')
def summit_edit(summit_id):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    f = forms.SummitForm(None, s, coordinates='{} {}'.format(s.lat, s.lng))
    f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    return render_template('summit_edit.html', form=f)

@app.route('/api/summits')
def summits_get():
    return jsonify(g.summits_dao.get_all(request.args.has_key('orderByHeight')))

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        pass
    
    registering_user = session.pop('registering_user', None)
    if registering_user is None:
        # TODO make it user-friendly
        return make_response('You should use social menu')
    else:
        form = forms.RegistrationForm(registering_user)
        return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('map'))

@app.route('/vk_login')
def vk_login():
    if 'error' in request.args.keys():
        return make_response(request.args.get('error_description'))
    
    params = {
            'client_id'    : app.config['VK_CLIENT_ID'],
            'client_secret': app.config['VK_CLIENT_SECRET'],
            'code'         : request.args.get('code'),
            'redirect_uri' : request.url_root + 'vk_login'
        }

    auth_data = auth.vk_get_access_token(params)
    if auth_data is None:
        return make_response('Error getting access token')

    oauth_id, email, access_token = auth_data

    # TODO remove magic number
    user = g.users_dao.get(oauth_id, 1)
    if user is None:
        profile = auth.vk_get_profile(oauth_id, access_token)
        user = UserMixin()
        user.oauth_id = profile['oauth_id']
        user.name = profile['name']
        user.src = 1
        user.email = email
        
        fd = urllib.urlopen(profile['image'])
        if fd.getcode() == 200:
            img_id = g.images_dao.create(fd.read(), fd.info().gettype())
        else:
            img_id = None

        user.img_id = img_id
        user.id = g.users_dao.create(user)

    login_user(user)
    return redirect(url_for('profile'))


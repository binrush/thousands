from thousands import app
from flask import request, render_template, g, jsonify, redirect, url_for, session, make_response, abort
from flask.ext.login import login_user, logout_user, current_user, UserMixin, login_required
import dao, auth, forms
import httplib, json, urllib

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/')
def index():
    return render_template('map.html')

@app.route('/table')
def table():
    return render_template('table.html', 
            summits=g.summits_dao.get_all(current_user, 
                request.args.has_key('orderByHeight')))

@app.route('/summit/<int:summit_id>')
def summit(summit_id):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    return render_template('summit.html', summit=s)

@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous() or not current_user.admin:
        abort(401)
    f = forms.SummitForm(request.form)
    f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    if request.method == 'POST' and f.validate():
        summit = Summit()
        return redirect(url_for('summit', g.summits_dao.create(summit)))
    return render_template('summit_edit.html', form=f)

@app.route('/summit/edit/<int:summit_id>', methods=['GET', 'POST'])
def summit_edit(summit_id):
    if current_user.is_anonymous() or not current_user.admin:
        abort(401)
    if request.method == 'POST':
        f = forms.SummitForm(request.form)
        f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
        if f.validate():
            summit = dao.Summit()
            f.populate_obj(summit)
            summit.lat, summit.lng = map(float, f.coordinates.data.split(' '))
            g.summits_dao.update(summit)
            return redirect(url_for('summit', summit_id=summit.id))
    else:
        s = g.summits_dao.get(summit_id)
        if s is None:
            return abort(404)
        f = forms.SummitForm(None, s, coordinates='{} {}'.format(s.lat, s.lng))
        f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    return render_template('summit_edit.html', form=f)

@app.route('/climb/new/<int:summit_id>')
@login_required
def climb_new(summit_id):
    f = forms.ClimbForm(request.form)
    if form.method == 'POST' and form.validate():
        g.climbs_dao.create(current_user, f.date.summit, f.date.data, f.comment.data)
        return redirect(url_for('summit', f.id))
    return render_template('climb_edit.html', 
            summit = g.summits_dao.get(summit_id),
            form = f)

@app.route('/api/summits')
def summits_get():
    return jsonify({ 'type': 'FeatureCollection', 
        'features': [ s.to_geojson() for s in g.summits_dao.get_all()] })

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

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

@app.route('/profile')
def profile():
    return render_template('profile.html')

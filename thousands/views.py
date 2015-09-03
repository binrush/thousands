from thousands import app
from flask import request, render_template, g, jsonify, redirect, url_for, session, make_response, abort, send_file
from flask.ext.login import login_user, logout_user, current_user, UserMixin, login_required
import dao, auth, forms
import httplib, json, urllib, io

@app.route('/about')
def about():
    return render_template('about.html', active_page='about')

@app.route('/')
def index():
    return render_template('map.html', active_page='index')

@app.route('/table')
def table():
    return render_template('table.html', 
            summits=g.summits_dao.get_all(current_user.get_id(), 
                request.args.has_key('orderByHeight')),
            active_page='table')

@app.route('/summit/<int:summit_id>')
def summit(summit_id):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    climbers = g.climbs_dao.climbers(summit_id)
    i = 0
    for c in climbers:
        if c['user'] == current_user:
            this = climbers.pop(i)
            climbers = [ this ] + climbers
        i += 1
    return render_template('summit.html',
            summit=s,
            climbers=climbers,
            active_page='table')

@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous() or not current_user.admin:
        abort(401)
    f = forms.SummitForm(request.form)
    f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    if request.method == 'POST' and f.validate():
        summit = dao.Summit()
        f.populate_obj(summit)
        summit.lat, summit.lng = f.coordinates.data
        return redirect(url_for('summit', summit_id=g.summits_dao.create(summit)))
    return render_template('summit_edit.html', form=f)

@app.route('/summit/edit/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def summit_edit(summit_id):
    if not current_user.admin:
        abort(401)
    if request.method == 'POST':
        f = forms.SummitForm(request.form)
        f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
        if f.validate():
            summit = dao.Summit()
            f.populate_obj(summit)
            g.summits_dao.update(summit)
            return redirect(url_for('summit', summit_id=summit.id))
    else:
        s = g.summits_dao.get(summit_id)
        if s is None:
            return abort(404)
        f = forms.SummitForm(None, s)
        f.rid.choices = [ (r['id'], r['name']) for r in g.summits_dao.get_ridges() ]
    return render_template('summit_edit.html', form=f)

@app.route('/summit/delete/<int:summit_id>')
@login_required
def summit_delete(summit_id):
    if not current_user.admin:
        abort(401)
    g.summits_dao.delete(summit_id)
    return redirect(url_for('index'))

@app.route('/climb/new/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def climb_new(summit_id):
    f = forms.ClimbForm(request.form)
    if request.method == 'POST' and f.validate():
        g.climbs_dao.create(current_user.get_id(), f.summit_id.data, f.date.data, f.comment.data)
        return redirect(url_for('summit', summit_id=f.summit_id.data))
    return render_template('climb_edit.html', 
            summit = g.summits_dao.get(summit_id),
            form = f)

@app.route('/climb/edit/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def climb_edit(summit_id):
    if request.method == 'POST':
        f = forms.ClimbForm(request.form)
        if f.validate():
            g.climbs_dao.update(
                    current_user.id, 
                    f.summit_id.data,
                    f.date.data,
                    f.comment.data)
            return redirect(url_for('summit', summit_id=f.summit_id.data))
    else:
        climb = g.climbs_dao.get(current_user.id, summit_id)
        f = forms.ClimbForm(None, climb, summit=summit_id)
    return render_template('climb_edit.html',
            summit = g.summits_dao.get(summit_id),
            form = f)

@app.route('/climb/delete/<int:summit_id>')
@login_required
def climb_delete(summit_id):
    g.climbs_dao.delete(current_user.id, summit_id)
    return redirect(url_for('summit', summit_id=summit_id))

@app.route('/api/summits')
def summits_get():
    return jsonify({ 'type': 'FeatureCollection', 
        'features': [ s.to_geojson() for s in g.summits_dao.get_all(current_user.get_id())] })

@app.route('/api/images/<int:image_id>')
def image_get(image_id):
    img = g.images_dao.get(image_id)
    return send_file(io.BytesIO(img.payload), mimetype=img.type)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    climbed = [ s for s in g.summits_dao.get_all(current_user.get_id()) if s.climbed ]
    return render_template('profile.html', climbed = climbed, active_page='profile')

@app.route('/user/<int:user_id>')
def user(user_id):
    abort(404)

@app.route('/top')
def top():
    climbers = g.climbs_dao.top()
    return render_template('top.html', climbers = climbers, active_page='top')

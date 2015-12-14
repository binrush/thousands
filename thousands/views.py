# coding: utf8
from thousands import app, summits_dao
from flask import (request, render_template, g, jsonify,
                   redirect, url_for, abort, send_file, flash)
from flask.ext.login import (logout_user, current_user,
                             login_required)
import dao
import forms
import io


@app.route('/about')
def about():
    return render_template('about.html', active_page='about')


@app.route('/')
def index():
    try:
        hl_summit = int(request.args['sid'])
    except (ValueError, TypeError, KeyError):
        hl_summit = None

    return render_template(
        'map.html',
        active_page='index',
        hl_summit=hl_summit)


@app.route('/table')
def table(summits_dao=summits_dao):
    sort = request.args.get('sort', 'ridge')
    return render_template(
        'table.html',
        summits=summits_dao.get_all(
            current_user.get_id(),
            sort),
        active_page='table',
        sort=sort)


@app.route('/summit/<int:summit_id>')
def summit(summit_id, summits_dao=summits_dao):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    climbers = g.climbs_dao.climbers(summit_id)
    i = 0
    for c in climbers:
        if c['user'] == current_user:
            this = climbers.pop(i)
            climbers = [this] + climbers
        i += 1
    return render_template(
        'summit.html',
        summit=s,
        climbers=climbers,
        active_page='table')


@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous() or not current_user.admin:
        abort(401)
    f = forms.SummitForm(request.form)
    f.rid.choices = [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    if request.method == 'POST' and f.validate():
        summit = dao.Summit()
        f.populate_obj(summit)
        summit.lat, summit.lng = f.coordinates.data
        return redirect(url_for('summit',
                                summit_id=g.summits_dao.create(summit)))
    return render_template('summit_edit.html', form=f)


@app.route('/summit/edit/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def summit_edit(summit_id):
    if not current_user.admin:
        abort(401)
    if request.method == 'POST':
        f = forms.SummitForm(request.form)
        f.rid.choices = \
            [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
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
        f.rid.choices = \
            [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
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
        g.climbs_dao.create(
            current_user.get_id(),
            f.summit_id.data,
            f.date.data,
            f.comment.data)
        flash(u'Ваше восхождение зарегистрировано')
        return redirect(url_for('summit', summit_id=f.summit_id.data))
    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=f)


@app.route('/summit/<int:summit_id>/climb/edit', methods=['GET', 'POST'])
@login_required
def summit_climb_edit(summit_id):
    return climb_edit(summit_id, url_for('summit', summit_id=summit_id))


@app.route('/climb/edit/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def profile_climb_edit(summit_id):
    return climb_edit(summit_id,
                      url_for('user', user_id=current_user.get_id(), _anchor=summit_id))


def climb_edit(summit_id, redirect_url):
    if request.method == 'POST':
        f = forms.ClimbForm(request.form)
        if f.validate():
            g.climbs_dao.update(
                current_user.id,
                f.summit_id.data,
                f.date.data,
                f.comment.data)
            flash(u'Ваше восхождение отредактировано')
            return redirect(redirect_url)
    else:
        climb = g.climbs_dao.get(current_user.id, summit_id)
        f = forms.ClimbForm(None, climb, summit=summit_id)
    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=f)


@app.route('/summit/<int:summit_id>/climb/delete/')
@login_required
def summit_climb_delete(summit_id):
    return climb_delete(summit_id, url_for('summit', summit_id=summit_id))


@app.route('/climb/delete/<int:summit_id>')
@login_required
def profile_climb_delete(summit_id):
    return climb_delete(summit_id,
                        url_for('user', user_id=current_user.get_id()))


def climb_delete(summit_id, redirect_url):
    g.climbs_dao.delete(current_user.id, summit_id)
    flash(u'Ваше восхождение удалено')
    return redirect(redirect_url)


@app.route('/api/summits')
def summits_get():
    return jsonify(
        {'type': 'FeatureCollection',
         'features':
            [s.to_geojson()
                for s in g.summits_dao.get_all(current_user.get_id())]})


@app.route('/api/images/<int:image_id>')
def image_get(image_id):
    img = g.images_dao.get(image_id)
    return send_file(io.BytesIO(img.payload), mimetype=img.type)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/user/<int:user_id>')
def user(user_id):
    user = g.users_dao.get_by_id(user_id)
    climbed = g.climbs_dao.climbed(user_id)
    return render_template(
        'user.html',
        user=user,
        climbed=climbed,
        active_page='top')


@app.route('/top')
def top():
    climbers = g.climbs_dao.top()
    return render_template('top.html', climbers=climbers, active_page='top')

# coding: utf8
from thousands import app
from flask import (request, render_template, g, jsonify,
                   redirect, url_for, abort, send_file, flash, session,
                   make_response)
from flask.ext.login import (logout_user, current_user,
                             login_required)
import dao
import forms
import mimetypes
from gpxpy.gpx import GPX


def move_to_front(l, fn):
    """
        Move list value to the beginning of list
    """
    i = 0
    for e in l:
        if fn(e):
            l.insert(0, l.pop(i))
            break
        i += 1
    return l


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


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
def table():
    sort = request.args.get('sort', 'ridge')
    return render_template(
        'table.html',
        summits=g.summits_dao.get_all(
            current_user.get_id(),
            sort),
        active_page='table',
        sort=sort)


@app.route('/summits/download')
def summits_download():
    return render_template(
        'download.html',
        active_page='table')


@app.route('/summit/<int:summit_id>')
def summit(summit_id):
    s = g.summits_dao.get(summit_id)
    if s is None:
        return abort(404)
    climbers = move_to_front(g.climbs_dao.climbers(summit_id),
                             lambda x: x['user'] == current_user)
    return render_template(
        'summit.html',
        summit=s,
        climbers=climbers,
        del_form=forms.DeleteForm(
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']}),
        active_page='table')


@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous or not current_user.admin:
        abort(401)
    f = forms.SummitForm(
        request.form,
        meta={'csrf_context': session,
              'csrf_secret': app.config['CSRF_SECRET']})
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
        f = forms.SummitForm(
            request.form,
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']})
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
        f = forms.SummitForm(
            None,
            s,
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']})
        f.rid.choices = \
            [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    return render_template('summit_edit.html', form=f)


@app.route('/summit/delete/<int:summit_id>', methods=['POST'])
@login_required
def summit_delete(summit_id):
    if not current_user.admin:
        abort(401)
    g.summits_dao.delete(summit_id)
    return redirect(url_for('index'))


@app.route('/climb/new/<int:summit_id>', methods=['GET', 'POST'])
def climb_new(summit_id):
    if not current_user.is_authenticated:
        return redirect(url_for('summit', summit_id=summit_id))

    if g.climbs_dao.get(current_user.get_id(), summit_id):
        flash(u'Вы уже сообщили о восхождении на эту вершину')
        return redirect(url_for('summit', summit_id=summit_id))

    f = forms.ClimbForm(
        request.form,
        meta={'csrf_context': session,
              'csrf_secret': app.config['CSRF_SECRET']})
    if request.method == 'POST' and f.validate():
        g.climbs_dao.create(
            current_user.get_id(),
            f.summit_id.data,
            f.date.data,
            f.comment.data)
        app.logger.info("Climb added uid=%s, sid=%s",
                        current_user.id,
                        summit_id)
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
                      url_for('user', user_id=current_user.get_id(),
                              _anchor=summit_id))


def climb_edit(summit_id, redirect_url):
    if request.method == 'POST':
        f = forms.ClimbForm(
            request.form,
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']})
        if f.validate():
            g.climbs_dao.update(
                current_user.id,
                f.summit_id.data,
                f.date.data,
                f.comment.data)
            app.logger.info("Climb edited uid=%s, sid=%s",
                            current_user.id,
                            summit_id)
            flash(u'Ваше восхождение отредактировано')
            return redirect(redirect_url)
    else:
        climb = g.climbs_dao.get(current_user.id, summit_id)
        f = forms.ClimbForm(
            None,
            climb,
            summit=summit_id,
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']})
    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=f)


@app.route('/summit/<int:summit_id>/climb/delete/', methods=['POST'])
@login_required
def summit_climb_delete(summit_id):
    return climb_delete(summit_id, url_for('summit', summit_id=summit_id))


@app.route('/climb/delete/<int:summit_id>', methods=['POST'])
@login_required
def profile_climb_delete(summit_id):
    return climb_delete(summit_id,
                        url_for('user', user_id=current_user.get_id()))


def climb_delete(summit_id, redirect_url):
    del_form = forms.DeleteForm(
        request.form,
        meta={'csrf_context': session,
              'csrf_secret': app.config['CSRF_SECRET']})
    if del_form.validate():
        g.climbs_dao.delete(current_user.id, summit_id)
        app.logger.info("Climb deleted uid=%s, sid=%s",
                        current_user.id,
                        summit_id)
        flash(u'Ваше восхождение удалено')
    else:
        flash(u'Invalid CSRF token', 'error')
    return redirect(redirect_url)


@app.route('/api/summits')
def summits_get():
    return jsonify(
        {'type': 'FeatureCollection',
         'features':
            [s.to_geojson()
                for s in g.summits_dao.get_all(current_user.get_id())]})


@app.route('/api/summits/gpx')
def summits_get_gpx():
    gpx = GPX()
    if 'rids' in request.args:
        rids = (int(rid) for rid in request.args['rids'].split(','))
        gpx.waypoints = \
            (s.to_gpx() for s in g.summits_dao.get_by_ridge(rids=rids))
    else:
        gpx.waypoints = \
            (s.to_gpx() for s in g.summits_dao.get_all())

    resp = make_response(gpx.to_xml())
    resp.mimetype = 'application/gpx+xml'
    resp.headers['Content-Disposition'] = \
        "attachment; filename=summits.gpx"
    return resp


@app.route('/api/images/<image_id>')
def image_get(image_id):
    img = g.images_dao.get(image_id)
    if img is None:
        return abort(404)
    return send_file(img.payload,
                     mimetype=mimetypes.guess_type(img.name)[0])


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/user/<int:user_id>')
def user(user_id):
    user = g.users_dao.get_by_id(user_id)
    if user is None:
        return abort(404)
    climbed = g.climbs_dao.climbed(user_id)
    return render_template(
        'user.html',
        user=user,
        climbed=climbed,
        del_form=forms.DeleteForm(
            meta={'csrf_context': session,
                  'csrf_secret': app.config['CSRF_SECRET']}),
        active_page='top')


@app.route('/user/image', methods=['POST'])
def image_upload():
    print request.files
    print request.form
    return "", 204


@app.route('/top')
def top():
    climbers = g.climbs_dao.top()
    return render_template('top.html', climbers=climbers, active_page='top')

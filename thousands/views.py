# coding: utf8
from __future__ import division
from thousands import app
from flask import (request, render_template, g, jsonify,
                   redirect, url_for, abort, send_file, flash,
                   make_response)
from flask.ext.login import (logout_user, current_user,
                             login_required)
import dao
import model
import forms
import mimetypes
import io
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


@app.errorhandler(413)
def file_too_large(e):
    if request.path == url_for('image_upload'):
        return jsonify({
            'state': 200,
            'message': 'Ошибка: превышен максимальный размер файла'}), 200
    else:
        return e, 404


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


# @app.route('/<ridge_id>')
# def ridge(ridge_id):
#     return render_template(
#         'ridge.html',
#         ridge=g.ridges_dao.get(ridge_id))
#
#
# @app.route('/ridges')
# def ridges():
#     return render_template(
#         'ridges.html',
#         active_page='ridges',
#         ridges=g.ridges_dao.get_all())


@app.route('/summits')
def table():
    sort = request.args.get('sort', 'ridge')
    return render_template(
        'table.html',
        summits=g.summits_dao.get_all(
            current_user.get_id(),
            sort),
        active_page='table',
        sort=sort)


@app.route('/<ridge_id>/<summit_id>')
def summit(ridge_id, summit_id):
    s = g.summits_dao.get(summit_id, True)
    if s is None:
        return abort(404)
    climbers = move_to_front(g.climbs_dao.climbers(summit_id),
                             lambda x: x['user'] == current_user)
    return render_template(
        'summit.html',
        summit=s,
        climbers=climbers,
        del_form=forms.DeleteForm(),
        active_page='table')


@app.route('/summits/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous or not current_user.admin:
        abort(401)
    form = forms.SummitForm()
    form.ridge_id.choices = \
        [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    if form.validate_on_submit():
        summit = dao.Summit()
        form.populate_obj(summit)
        summit.lat, summit.lng = form.coordinates.data
        summit = g.summits_dao.create(summit)
        return redirect(url_for('summit',
                                ridge_id=summit.ridge_id,
                                summit_id=summit.id))
    return render_template('summit_edit.html', form=form)


@app.route('/<ridge_id>/<summit_id>/edit', methods=['GET', 'POST'])
@login_required
def summit_edit(ridge_id, summit_id):
    print dir(request.url_rule)
    if not current_user.admin:
        abort(401)

    summit = g.summits_dao.get(summit_id)
    if summit is None:
        abort(404)
    form = forms.SummitForm(obj=summit)
    form.ridge_id.choices = \
        [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    if form.validate_on_submit():
        summit = dao.Summit()
        summit.id = summit_id
        form.populate_obj(summit)
        g.summits_dao.update(summit)
        return redirect(url_for('summit',
                                summit_id=summit.id,
                                ridge_id=summit.ridge_id))

    return render_template('summit_edit.html', form=form)


@app.route('/<ridge_id>/<summit_id>/delete', methods=['POST'])
@login_required
def summit_delete(ridge_id, summit_id):
    if not current_user.admin:
        abort(401)
    form = forms.DeleteForm()
    if form.validate_on_submit():
        g.summits_dao.delete(summit_id)
    return redirect(url_for('index'))


@app.route('/<ridge_id>/<summit_id>/images', methods=['GET', 'POST'])
@login_required
def summit_images(ridge_id, summit_id):
    if not current_user.admin:
        abort(401)
    form = forms.SummitImageUploadForm()
    if form.validate_on_submit():
        fd = form.image.data
        image = model.Image.modified(fd, thumbnail=(800, 800))
        fd.seek(0)
        preview = model.Image.modified(fd, thumbnail=(75, 75))

        g.images_dao.create(image)
        g.images_dao.create(preview)

        g.summits_images_dao.create(model.SummitImage(
            image=image.name,
            preview=preview.name,
            summit_id=summit_id,
            comment=form.comment.data,
            main=form.main.data))
        return redirect(url_for('summit_images',
                                summit_id=summit_id,
                                ridge_id=ridge_id))

    return render_template('summit_images.html',
                           form=form,
                           summit=g.summits_dao.get(summit_id, True))


@app.route('/<ridge_id>/<summit_id>/images/<image_id>/edit',
           methods=['GET', 'POST'])
def summit_image_edit(ridge_id, summit_id, image_id):
    summit_image = g.summits_images_dao.get(image_id)
    form = forms.SummitImageEditForm(obj=summit_image)
    if form.validate_on_submit():
        if form.action.data == 'delete':
            g.images_dao.delete(summit_image.image)
            g.images_dao.delete(summit_image.preview)
            g.summits_images_dao.delete(image_id)
        elif form.action.data == 'update':
            g.summits_images_dao.update(image_id,
                                        form.comment.data,
                                        form.main.data)
        return redirect(url_for('summit_images',
                                ridge_id=ridge_id,
                                summit_id=summit_id))

    return render_template(
        'summit_image_edit.html',
        summit=g.summits_dao.get(summit_image.summit_id),
        image=image_id,
        form=form)


@app.route('/<ridge_id>/<summit_id>/climb', methods=['GET', 'POST'])
def climb_new(ridge_id, summit_id):
    if not current_user.is_authenticated:
        return redirect(url_for('summit',
                                ridge_id=ridge_id,
                                summit_id=summit_id))

    summit = g.summits_dao.get(summit_id)
    if g.climbs_dao.get(current_user, summit):
        flash(u'Вы уже сообщили о восхождении на эту вершину')
        return redirect(url_for('summit',
                                ridge_id=ridge_id,
                                summit_id=summit_id))

    form = forms.ClimbForm()
    if form.validate_on_submit():
        g.climbs_dao.create(
            current_user,
            g.summits_dao.get(summit_id),
            form.date.data,
            form.comment.data)
        app.logger.info("Climb added uid=%s, summit_id=%s",
                        current_user.id, summit_id)
        flash(u'Ваше восхождение зарегистрировано')
        return redirect(url_for('summit',
                                ridge_id=ridge_id,
                                summit_id=summit_id))

    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=form)


@app.route('/<ridge_id>/<summit_id>/climb/edit', methods=['GET', 'POST'])
@login_required
def summit_climb_edit(ridge_id, summit_id):
    return climb_edit(summit_id,
                      url_for('summit',
                              ridge_id=ridge_id,
                              summit_id=summit_id))


@app.route('/climb/<ridge_id>/<summit_id>/edit', methods=['GET', 'POST'])
@login_required
def profile_climb_edit(summit_id):
    return climb_edit(summit_id,
                      url_for('user', user_id=current_user.get_id(),
                              _anchor=summit_id))


def climb_edit(summit_id, redirect_url):
    summit = g.summits_dao.get(summit_id)
    climb = g.climbs_dao.get(current_user, summit)
    form = forms.ClimbForm(obj=climb)
    if form.validate_on_submit():
        g.climbs_dao.update(
            current_user.id,
            summit_id,
            form.date.data,
            form.comment.data)
        app.logger.info("Climb edited uid=%s, sid=%s",
                        current_user.id,
                        summit_id)
        flash(u'Ваше восхождение отредактировано')
        return redirect(redirect_url)
    return render_template('climb_edit.html',
                           summit=summit,
                           form=form)


@app.route('/<ridge_id>/<summit_id>/climb/delete', methods=['POST'])
@login_required
def summit_climb_delete(ridge_id, summit_id):
    return climb_delete(summit_id,
                        url_for('summit',
                                ridge_id=ridge_id,
                                summit_id=summit_id))


@app.route('/climb/<ridge_id>/<summit_id>/delete', methods=['POST'])
@login_required
def profile_climb_delete(ridge_id, summit_id):
    return climb_delete(summit_id,
                        url_for('user', user_id=current_user.get_id()))


def climb_delete(summit_id, redirect_url):
    del_form = forms.DeleteForm()
    if del_form.validate_on_submit():
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
    return send_file(io.BytesIO(img.payload),
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
    params = dict(
        user=user,
        climbed=climbed,
        del_form=forms.DeleteForm(),
        active_page='top')
    if user == current_user:
        params['image_form'] = forms.ImageUploadForm()
    return render_template('user.html', **params)


@app.route('/user/image', methods=['POST'])
def image_upload():
    form = forms.ImageUploadForm()

    if not form.validate_on_submit():
        app.logger.warn('Avatar upload: form validation failed:' +
                        str(form.errors))
        return abort(400)

    box = (
        form.x.data,
        form.y.data,
        form.x.data + form.width.data,
        form.y.data + form.height.data
    )
    fs = form.image.data

    image = model.Image.modified(fs, size=(200, None))
    fs.seek(0)
    preview = model.Image.modified(fs, size=(50, 50), crop=box)

    g.images_dao.create(image)
    g.images_dao.create(preview)

    g.images_dao.delete(current_user.image)
    current_user.image = image.name

    g.images_dao.delete(current_user.preview)
    current_user.preview = preview.name

    g.users_dao.update(current_user)

    return jsonify({'state': 200,
                    'message': 'Success',
                    'result': url_for('image_get',
                                      image_id=current_user.image)})


@app.route('/top')
def top():
    climbers = g.climbs_dao.top()
    return render_template('top.html', climbers=climbers, active_page='top')

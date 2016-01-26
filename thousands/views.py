# coding: utf8
from __future__ import division
from thousands import app
from flask import (request, render_template, g, jsonify,
                   redirect, url_for, abort, send_file, flash,
                   make_response)
from flask.ext.login import (logout_user, current_user,
                             login_required)
import dao
import forms
import mimetypes
from gpxpy.gpx import GPX
from PIL import Image
from io import BytesIO
import hashlib


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


def save_image(images_dao, img, fmt):
    data = BytesIO()
    img.save(data, fmt, quality=90)
    img_filename = hashlib.sha1(data.getvalue()).hexdigest() + '.' + \
        fmt.lower()
    images_dao.create(img_filename, data.getvalue())
    return img_filename


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


@app.route('/summit/<int:summit_id>')
def summit(summit_id):
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


@app.route('/summit/new', methods=['GET', 'POST'])
def summit_new():
    if current_user.is_anonymous or not current_user.admin:
        abort(401)
    form = forms.SummitForm()
    form.rid.choices = \
        [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    if form.validate_on_submit():
        summit = dao.Summit()
        form.populate_obj(summit)
        summit.lat, summit.lng = form.coordinates.data
        return redirect(url_for('summit',
                                summit_id=g.summits_dao.create(summit)))
    return render_template('summit_edit.html', form=form)


@app.route('/summit/edit/<int:summit_id>', methods=['GET', 'POST'])
@login_required
def summit_edit(summit_id):
    if not current_user.admin:
        abort(401)

    s = g.summits_dao.get(summit_id)
    if s is None:
        abort(404)
    form = forms.SummitForm(obj=g.summits_dao.get(summit_id))
    form.rid.choices = \
        [(r['id'], r['name']) for r in g.summits_dao.get_ridges()]
    if form.validate_on_submit():
        summit = dao.Summit()
        form.populate_obj(summit)
        g.summits_dao.update(summit)
        return redirect(url_for('summit', summit_id=summit.id))

    return render_template('summit_edit.html', form=form)


@app.route('/summit/delete/<int:summit_id>', methods=['POST'])
@login_required
def summit_delete(summit_id):
    if not current_user.admin:
        abort(401)
    form = forms.DeleteForm()
    if form.validate_on_submit():
        g.summits_dao.delete(summit_id)
    return redirect(url_for('index'))


@app.route('/summit/<int:summit_id>/images', methods=['GET', 'POST'])
@login_required
def summit_images(summit_id):
    if not current_user.admin:
        abort(401)
    form = forms.SummitImageUploadForm()
    if form.validate_on_submit():
        img = Image.open(request.files['image'])
        fmt = img.format
        image_name = save_image(g.images_dao, img, fmt)
        img.thumbnail((75, 75))
        preview_name = save_image(g.images_dao, img, fmt)
        g.summits_dao.create_image(
            form.summit_id.data,
            image_name,
            preview_name,
            form.comment.data)
        return redirect(url_for('summit', summit_id=form.summit_id.data))

    return render_template('summit_images.html',
                           form=form,
                           summit=g.summits_dao.get(summit_id, True))


@app.route('/summit/image/edit/<image_id>',
           methods=['GET', 'POST'])
def summit_image_edit(image_id):
    summit_image = g.summits_dao.get_image(image_id)
    form = forms.SummitImageEditForm(obj=summit_image)
    if form.validate_on_submit():
        if form.action.data == 'delete':
            g.images_dao.delete(summit_image.image)
            g.images_dao.delete(summit_image.preview)
            g.summits_dao.delete_image(image_id)
        elif form.action.data == 'update':
            g.summits_dao.update_image(image_id, form.comment.data)
        return redirect(url_for('summit_images',
                                summit_id=summit_image.summit_id))

    return render_template(
        'summit_image_edit.html',
        summit=g.summits_dao.get(summit_image.summit_id),
        image=image_id,
        form=form)


@app.route('/climb/new/<int:summit_id>', methods=['GET', 'POST'])
def climb_new(summit_id):
    if not current_user.is_authenticated:
        return redirect(url_for('summit', summit_id=summit_id))

    if g.climbs_dao.get(current_user.get_id(), summit_id):
        flash(u'Вы уже сообщили о восхождении на эту вершину')
        return redirect(url_for('summit', summit_id=summit_id))

    form = forms.ClimbForm()
    if form.validate_on_submit():
        g.climbs_dao.create(
            current_user.get_id(),
            form.summit_id.data,
            form.date.data,
            form.comment.data)
        app.logger.info("Climb added uid=%s, sid=%s",
                        current_user.id,
                        summit_id)
        flash(u'Ваше восхождение зарегистрировано')
        return redirect(url_for('summit', summit_id=form.summit_id.data))

    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=form)


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
    climb = g.climbs_dao.get(current_user.id, summit_id)
    form = forms.ClimbForm(obj=climb)
    if form.validate_on_submit():
        g.climbs_dao.update(
            current_user.id,
            form.summit_id.data,
            form.date.data,
            form.comment.data)
        app.logger.info("Climb edited uid=%s, sid=%s",
                        current_user.id,
                        summit_id)
        flash(u'Ваше восхождение отредактировано')
        return redirect(redirect_url)
    return render_template('climb_edit.html',
                           summit=g.summits_dao.get(summit_id),
                           form=form)


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

    if not form.validate():
        return abort(400)

    box = (
        form.x.data,
        form.y.data,
        form.x.data + form.width.data,
        form.y.data + form.height.data
    )
    img = Image.open(request.files['image'])
    fmt = img.format

    if fmt not in ('PNG', 'JPEG', 'GIF'):
        return abort(400)

    preview = img.crop(box).resize((50, 50), Image.ANTIALIAS)
    img = img.resize((200, int(img.size[1]/(img.size[0]/200))),
                     Image.ANTIALIAS)

    image_name = save_image(g.images_dao, img, fmt)
    preview_name = save_image(g.images_dao, preview, fmt)

    g.images_dao.delete(current_user.image)
    current_user.image = image_name

    g.images_dao.delete(current_user.preview)
    current_user.preview = preview_name

    g.users_dao.update(current_user)

    return jsonify({'state': 200,
                    'message': 'Success',
                    'result': url_for('image_get',
                                      image_id=current_user.image)})


@app.route('/top')
def top():
    climbers = g.climbs_dao.top()
    return render_template('top.html', climbers=climbers, active_page='top')

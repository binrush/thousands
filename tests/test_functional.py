# coding: utf-8
import json
import pytest
import thousands


@pytest.fixture(scope="module", autouse=True)
def enable_testing():
    thousands.app.config['SECRET_KEY'] = 'test-secret-key'
    thousands.app.config['TESTING'] = True
    thousands.app.config['WTF_CSRF_ENABLED'] = False


@pytest.fixture(scope="module", autouse=True)
def populate_database(request):
    conn = thousands.pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(u"INSERT INTO ridges (id, name, color) \
                    VALUES (1, 'Крыкты-Тау', 'fafafa')")
        cur.execute(u"INSERT INTO users (id, oauth_id, src, name) \
                    VALUES (1, 12345, 1, 'Иван Кузнецов')")
        cur.execute(u"INSERT INTO users (id, oauth_id, src, name, admin) \
                    VALUES (2, '54321', 1, 'admin', true)")
        cur.execute(u"INSERT INTO summits (rid, name, height, \
                    description, interpretation, lng, lat) VALUES \
                    (1, 'Бабай', 1015, 'Невысокая скала', \
                    'Дедушка, старейшина', 53.1, 58.1), \
                    (1, 'Noname', 1007, NULL, NULL, 53.2, 58.2), \
                    (1, 'Кушай', 1048, 'Три скальных гребня', \
                    'Двойной', 53.3, 58.3)")
        cur.execute(u"INSERT INTO climbs (user_id, summit_id, comment, \
                    year, month, day)\
                    select 1, id, 'Fun', 2011, 11, NULL\
                    FROM summits WHERE name='Кушай';")
        conn.commit()
    finally:
            thousands.pool.putconn(conn)

    def cleanup():
        conn = thousands.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM climbs")
            cur.execute("DELETE FROM users")
            cur.execute("DELETE FROM summits")
            cur.execute("DELETE FROM ridges")
            conn.commit()
        finally:
            thousands.pool.putconn(conn)

    request.addfinalizer(cleanup)


@pytest.fixture(scope="module")
def client_anonymous():
    return thousands.app.test_client()


def client_authenticated(user_id):
    with thousands.app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = user_id
        return c


@pytest.fixture(scope="module")
def client_user():
    return client_authenticated(u'1')


@pytest.fixture(scope="module")
def client_admin():
    return client_authenticated(u'2')


def get_summit_id(client, name):
    summits = json.loads(client.get('/api/summits').data)
    for s in summits['features']:
        if s['properties']['name'] == name:
            return s['id']


def test_summit_new_reject_anonymous(client_anonymous):
    resp = client_anonymous.get('/summit/new')
    assert resp.status == '401 UNAUTHORIZED'


def test_summit_new_reject_nonadmin(client_user):
    resp = client_user.get('/summit/new')
    assert resp.status == '401 UNAUTHORIZED'


def test_summit_new_get_shows_form(client_admin):
    resp = client_admin.get('/summit/new')
    assert resp.status == '200 OK'
    assert '<option value="1">Крыкты-Тау</option>' in resp.data
    assert '<div id="coordinates-pick-map"' in resp.data


def test_summit_new_post_shows_message_on_err(client_admin):
    resp = client_admin.post('/summit/new', data={"name": "Караташ"})
    assert resp.status == '200 OK'
    assert 'value="Караташ' in resp.data
    assert '<ul id="form-error-list">'
    assert 'Number must be between 1000 and 1640.' in resp.data


def test_summit_new_post_add_summit(client_admin):
    resp = client_admin.post('/summit/new', data={
        "name": "Караташ",
        "coordinates": "54.123456 58.654321",
        "height": "1010",
        "rid": "1"})
    assert resp.status == "302 FOUND"
    resp = client_admin.get(resp.headers['Location'])
    assert resp.status == "200 OK"
    assert '<dd>1010' in resp.data
    assert 'Караташ' in resp.data


def test_table(client_user):
    resp = client_user.get('/table')
    assert resp.status == "200 OK"
    assert resp.data.index('Кушай') < \
        resp.data.index('1007') < \
        resp.data.index('Бабай')
    resp = client_user.get('/table?sort=height')
    assert resp.data.index('Вы взошли на эту вершину') < \
        resp.data.index('Кушай') < \
        resp.data.index('Бабай') < \
        resp.data.index('1007')


def test_summits_api(client_user):
    resp = client_user.get('/api/summits')
    assert resp.status == '200 OK'
    assert resp.content_type == 'application/json'
    data = json.loads(resp.data)
    assert len(data['features']) >= 3
    for s in data['features']:
        if s['properties']['name'] == u'Кушай':
            assert s['properties']['height'] == 1048
            assert s['properties']['climbed']
            assert s['properties']['main']
            assert s['properties']['color'] == 'fafafa'
            break
        raise Exception("Summit not found")


def test_summit_not_climbed(client_user):
    summit_id = get_summit_id(client_user, u'Бабай')
    resp = client_user.get('/summit/' + str(summit_id))
    assert resp.status == '200 OK'
    assert '<a class="btn btn-primary" ' + \
        'href="/climb/new/{}">Взошли на эту вершину?</a>'.format(summit_id) in \
        resp.data
    assert '<dd>1015' in resp.data
    assert 'Бабай' in resp.data


def test_summit_climbed(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.get('/summit/' + str(summit_id))
    assert resp.status == '200 OK'
    assert 'href="/summit/{}/climb/edit"'.format(summit_id) in resp.data
    assert not ('Взошли на эту вершину?' in resp.data)


def test_summit_anonymous(client_anonymous):
    summit_id = get_summit_id(client_anonymous, u'Бабай')
    resp = client_anonymous.get('/summit/' + str(summit_id))
    assert resp.status == '200 OK'
    assert 'href="/login?r=%2Fclimb%2Fnew%2F{}"'.format(summit_id) in resp.data
    assert 'Взошли на эту вершину?' in resp.data


def test_climb_form_anonymous(client_anonymous):
    summit_id = get_summit_id(client_anonymous, u'Бабай')
    resp = client_anonymous.get('/climb/new/' + str(summit_id))
    assert resp.status == '302 FOUND'
    resp = client_anonymous.get('/climb/edit/' + str(summit_id))
    assert resp.status == '401 UNAUTHORIZED'
    resp = client_anonymous.get('/summit/{}/climb/edit'.format(summit_id))
    assert resp.status == '401 UNAUTHORIZED'


def test_climb_form_user(client_user):
    summit_id = get_summit_id(client_user, u'Бабай')
    resp = client_user.get('/climb/new/' + str(summit_id))
    assert resp.status == '200 OK'
    assert '<input id="summit_id" name="summit_id" ' + \
           'type="hidden" value="{}">'.format(summit_id) in resp.data


def test_climb_form_user_existing(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.get('/climb/new/' + str(summit_id))
    assert resp.status == '302 FOUND'
    assert '/summit/' + str(summit_id) in resp.headers['Location']


def test_climb_add(client_user):
    summit_id = get_summit_id(client_user, u'Бабай')
    resp = client_user.post('/climb/new/{}'.format(summit_id), data={
        'summit_id': str(summit_id),
        'date': '10.10.2010',
        'comment': 'nice'})
    assert resp.status == '302 FOUND'
    assert '/summit/' + str(summit_id) in resp.headers['Location']
    resp = client_user.get(resp.headers['Location'])
    assert resp.status == '200 OK'
    assert 'Бабай' in resp.data
    assert '<a href="/summit/{}/climb/edit">Редактировать'.format(summit_id) \
        in resp.data


@pytest.mark.xfail()
def test_climb_add_wo_token(client_user):
    summit_id = get_summit_id(client_user, u'Noname')
    resp = client_user.post('/climb/new/{}'.format(summit_id), data={
        'summit_id': str(summit_id),
        'date': '10.10.2010',
        'comment': 'nice'})
    assert resp.status == '200 OK'
    assert 'CSRF token missing' in resp.data


def test_climb_edit_form(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.get('/climb/edit/{}'.format(summit_id))
    assert resp.status == '200 OK'
    assert 'value="11.2011"' in resp.data
    assert '>Fun</textarea>' in resp.data


def test_climb_edit_post(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.post('/climb/edit/{}'.format(summit_id), data={
        'summit_id': str(summit_id),
        'date': '10.10.2010',
        'comment': 'Nice'})
    assert resp.status == '302 FOUND'
    resp = client_user.get('/climb/edit/{}'.format(summit_id))
    assert resp.status == '200 OK'
    assert 'value="10.10.2010"' in resp.data
    assert '>Nice</textarea>' in resp.data


@pytest.mark.xfail()
def test_climb_edit_wo_token(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.post('/climb/edit/{}'.format(summit_id), data={
        'summit_id': str(summit_id),
        'date': '10.10.2010',
        'comment': 'nice'})
    assert resp.status == '200 OK'
    assert 'CSRF token missing' in resp.data


def test_climb_delete(client_user):
    summit_id = get_summit_id(client_user, 'Noname')
    resp = client_user.post('/climb/new/{}'.format(summit_id), data={
        'summit_id': str(summit_id),
        'date': '',
        'comment': ''})
    assert resp.status == '302 FOUND'
    resp = client_user.post('/climb/delete/{}'.format(summit_id), data={})
    assert resp.status == '302 FOUND'
    resp = client_user.get(resp.headers['Location'])
    assert not ('Noname' in resp.data)


@pytest.mark.xfail()
def test_climb_delete_wo_token(client_user):
    summit_id = get_summit_id(client_user, u'Кушай')
    resp = client_user.post('/climb/delete/{}'.format(summit_id), data={})
    assert resp.status == '302 FOUND'
    resp = client_user.get(resp.headers['Location'])
    assert 'Invalid CSRF token' in resp.data

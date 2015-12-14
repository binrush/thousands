import pytest
import mock
import thousands
from thousands import views

# def setUp(self):
#     with patch('psycopg2.pool.SimpleConnectionPool',
#                lambda x, y, z: MagicMock()):
#         import thousands
#         thousands.app.config['SECRET_KEY'] = 'fake-secret-key'
#         thousands.app.config['TESTING'] = True
#         self.app = thousands.app.test_client()


@pytest.fixture
def client():
    thousands.app.config['TESTING'] = True
    thousands.app.config['SECRET_KEY'] = 'test-secret-key'
    return thousands.app.test_client

@pytest.fixture
def mock_users_dao():
    ud = mock.MagicMock()
    u = mock.MagicMock()
    u.get_id.return_value=u'5'
    ud.get_by_id.return_value = u
    return ud


def test_move_to_front():
    l = [1, 6, 7, 2, 4]
    assert views.move_to_front(l, lambda x: x == 6) == \
        [6, 1, 7, 2, 4]
    assert views.move_to_front(l, lambda x: x == 5) == l
    assert views.move_to_front([], lambda x: x == 5) == []


def test_index(client):
    rv = client().get('/')
    assert "document.body.onload = createMainMap;" in rv.data


@mock.patch('thousands.users_dao', new=mock_users_dao())
@mock.patch('thousands.summits_dao')
def test_table(mock_summits_dao, mock_users_dao, client):
    #mock_users_dao.get_by_id.return_value = mock_user    
    with client() as c:
        c.get('/table')
        mock_summits_dao.get_all.assert_called_with(None, 'ridge')
        with c.session_transaction() as sess:
            sess['user_id'] = u'5'
        c.get('/table?sort=name')
        mock_summits_dao.get_all.assert_called_with(u'5', 'name')


@mock.patch('thousands.summits_dao')
def test_summit_returns_404_on_nonexistent(mock_summits_dao, client):
    mock_summits_dao.get = mock.MagicMock(return_value=None)
    with client() as c:
        resp = c.get('/summit/1')
        mock_summits_dao.get.assert_called_with(1)
        assert resp.status == '404 NOT FOUND'


@mock.patch('thousands.climbs_dao')
@mock.patch('thousands.summits_dao')
def test_summit(mock_summits_dao, mock_climbs_dao, client):
    with client() as c:
        c.get('/summit/1')
        mock_summits_dao.get.assert_called_with(1)
        mock_climbs_dao.climbers.assert_called_with(1)


@mock.patch('thousands.summits_dao')
def test_climb_new(mock_summits_dao, client):
    with client() as c:
        resp = c.get('/climb/new/2')
        mock_summits_dao.asssert_called_with('abc')
        assert resp.status == '401 UNAUTHORIZED'
        # c.post('/climb/new/1', data=dict())

import pytest
import thousands


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
    return thousands.app.test_client()


def test_index(client):
    rv = client.get('/')
    assert "document.body.onload = createMainMap;" in rv.data

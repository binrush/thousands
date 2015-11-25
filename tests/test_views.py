from mock import patch, MagicMock
import unittest


class ViewsTestCase(unittest.TestCase):

    def setUp(self):
        with patch('psycopg2.pool.SimpleConnectionPool',
                   lambda x, y, z: MagicMock()):
            import thousands
            thousands.app.config['SECRET_KEY'] = 'fake-secret-key'
            thousands.app.config['TESTING'] = True
            self.app = thousands.app.test_client()

    def test_index(self):
        rv = self.app.get('/')
        assert "document.body.onload = createMainMap;" in rv.data

#    def test_table(self):
#        rv = self.app.get('/table')
#        assert "Yamantau" in rv.data

if __name__ == '__main__':
    unittest.main()

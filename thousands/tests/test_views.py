import unittest
import thousands

class ViewsTestCase(unittest.TestCase):

    def setUp(self):
        thousands.app.config['TESTING'] = True
        self.app = thousands.app.test_client()

    def test_index(self):
        rv = self.app.get('/')
        assert "document.body.onload = createMainMap;" in rv.data

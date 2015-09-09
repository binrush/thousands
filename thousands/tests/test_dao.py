import unittest
from thousands import dao

class SummitTestCase(unittest.TestCase):

    def setUp(self):
        self.summit = dao.Summit()
        self.summit.name = "Small Yamantau"
        self.summit.height = 1519
        self.summit.name_alt = "Kuyantau"

    def tearDown(self):
        pass

    def test_format_name_when_name_exists(self):
        assert self.summit.format_name() == "Small Yamantau"

if __name__ == '__main__':
    unittest.main()


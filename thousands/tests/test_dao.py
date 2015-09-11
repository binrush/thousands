import unittest
from thousands import dao

class SummitTestCase(unittest.TestCase):

    def setUp(self):
        self.summit1 = dao.Summit()
        self.summit1.id = 1
        self.summit1.name = "Small Yamantau"
        self.summit1.height = 1519
        self.summit1.name_alt = "Kuyantau"
        self.summit1.coordinates = (53.1111, 58.2222)
        self.summit1.ridge = 'Yamantau'
        self.summit1.rid = 1
        self.summit1.color = 'aaaaaa'
        self.summit1.climbed = False

        self.summit2 = dao.Summit()
        self.summit2.name = ''
        self.summit2.height = 1111
        self.summit2.name_alt = ''

    def tearDown(self):
        pass

    def test_format_name_when_name_exists(self):
        assert self.summit1.format_name() == "Small Yamantau"

    def test_format_name_when_only_height(self):
        assert self.summit2.format_name() == "1111"

    def test_format_name_alt_when_exists(self):
        assert self.summit1.format_name_alt() == "(Kuyantau)"

    def test_format_name_alt_when_not_exists(self):
        assert self.summit2.format_name_alt() == ""

    def test_togeojson(self):
        assert self.summit1.to_geojson() ==  \
            {'geometry': 
                    {'type': 'Point', 'coordinates': [58.2222, 53.1111]}, 
            'type': 'Feature', 
            'properties': {
                'ridge': 'Yamantau', 
                'name': 'Small Yamantau', 
                'color': 'aaaaaa', 
                'climbed': False, 
                'height': 1519, 
                'name_alt': '(Kuyantau)'}, 
            'id': 1}


if __name__ == '__main__':
    unittest.main()


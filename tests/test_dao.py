import unittest
from thousands import dao


class InexactDateTestCase(unittest.TestCase):
    def test_init(self):
        ied = dao.InexactDate(2010, 10, 10)
        assert ied.year == 2010
        assert ied.month == 10
        assert ied.day == 10

    def test_init_wrong(self):
        self.assertRaises(ValueError, dao.InexactDate, 2010, 13)
        self.assertRaises(ValueError, dao.InexactDate, 2010, day=31)
        self.assertRaises(ValueError, dao.InexactDate, 2015, 2, 29)

    def test_parse(self):
        ied = dao.InexactDate.fromstring('2010')
        assert ied.year == 2010 and ied.month is None and ied.day is None
        ied = dao.InexactDate.fromstring('2.2010')
        assert ied.year == 2010 and ied.month == 2 and ied.day is None
        ied = dao.InexactDate.fromstring('12.06.2014')
        assert ied.year == 2014 and ied.month == 6 and ied.day == 12

        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          'some wrong input')
        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          '10..2010')
        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          '29.2.2015')

    def test_tuple(self):
        ied = dao.InexactDate(2010, 6, 12)
        assert ied.tuple() == (2010, 6, 12)

    def test_cmp(self):
        assert dao.InexactDate(2010, 10, 10) is not None


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
        self.summit1.main = False

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
                 'main': False,
                 'height': 1519,
                 'name_alt': '(Kuyantau)'},
             'id': 1}


if __name__ == '__main__':
    unittest.main()

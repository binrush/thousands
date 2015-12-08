# coding: utf8
import unittest
from thousands import dao
from mock import MagicMock


class InexactDateTestCase(unittest.TestCase):
    def test_init(self):
        ied = dao.InexactDate(2010, 10, 10)
        assert ied.year() == 2010
        assert ied.month() == 10
        assert ied.day() == 10

    def test_init_wrong(self):
        self.assertRaises(ValueError, dao.InexactDate, 2010, 13)
        self.assertRaises(ValueError, dao.InexactDate, 2015, 2, 29)

    def test_fromstring(self):
        ied = dao.InexactDate.fromstring('2010')
        assert ied.year() == 2010 and ied.month() is None and ied.day() is None
        ied = dao.InexactDate.fromstring('2.2010')
        assert ied.year() == 2010 and ied.month() == 2 and ied.day() is None
        ied = dao.InexactDate.fromstring('12.06.2014')
        assert ied.year() == 2014 and ied.month() == 6 and ied.day() == 12
        ied = dao.InexactDate.fromstring('')
        assert ied.year() is None and ied.month() is None and ied.day() is None

        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          'some wrong input')
        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          '10..2010')
        self.assertRaises(ValueError,
                          dao.InexactDate.fromstring,
                          '29.2.2015')

    def test_fromdict(self):
        ied = dao.InexactDate.fromdict(
            {'year': 2010, 'month': 10, 'day': 10})
        assert ied.year() == 2010 and ied.month() == 10 and ied.day() == 10
        ied = dao.InexactDate.fromdict(
            {'year': 2010, 'month': 10, 'day': None})
        assert ied.year() == 2010 and ied.month() == 10 and ied.day() is None
        ied = dao.InexactDate.fromdict(
            {'year': 2010, 'month': None, 'day': None})
        assert ied.year() == 2010 and ied.month() is None and ied.day() is None
        ied = dao.InexactDate.fromdict(
            {'year': None, 'month': None, 'day': None})
        assert not ied
        assert len(ied) == 0

    def test_format(self):
        ied = dao.InexactDate(2010)
        assert ied.format() == u'2010'
        ied = dao.InexactDate(2010, 10)
        assert ied.format() == u'Октябрь 2010'
        ied = dao.InexactDate(2010, 10, 10)
        assert ied.format() == u'10 Октября 2010'


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
                 'height': 1519
                 },
             'id': 1}

    def test_format_coordinates(self):
        assert self.summit1.format_coordinates() == \
            u"53.1111 58.2222 (53\u00b06'39.96''N 58\u00b013'19.92''E)"


class SummitDaoTestCase(unittest.TestCase):

    def test_row2summit(self):
        row = {'id': 1, 'height': 1640, 'ridge': "Yamantau",
               "lat": 65.4321, "lng": 12.3456}
        sd = dao.SummitsDao(MagicMock())
        summit = sd._SummitsDao__row2summit(row)
        assert summit.id == 1
        assert summit.ridge == "Yamantau"
        assert summit.coordinates == (65.4321, 12.3456)

    def test_rate_by_field(self):
        sd = dao.SummitsDao(MagicMock())
        s1 = dao.Summit()
        s1.name = "Summit1"
        s1.height = 1000
        s2 = dao.Summit()
        s2.name = "Summit2"
        s2.height = 1640
        s3 = dao.Summit()
        s3.name = "Summit3"
        s3.height = 1582
        sl = [s1, s2, s3]
        res = sd._SummitsDao__rate_by_field(sl, 'height')
        assert res[0].number == 3
        assert res[1].number == 1
        assert res[2].number == 2

if __name__ == '__main__':
    unittest.main()

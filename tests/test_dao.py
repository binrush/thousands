# coding: utf8
from thousands import dao
from mock import MagicMock
import pytest


class TestInexactDate():
    def test_init(self):
        ied = dao.InexactDate(2010, 10, 10)
        assert ied.year() == 2010
        assert ied.month() == 10
        assert ied.day() == 10

    def test_init_wrong(self):
        with pytest.raises(ValueError):
            dao.InexactDate(2010, 13)
        with pytest.raises(ValueError):
            dao.InexactDate(2015, 2, 29)

    def test_fromstring(self):
        ied = dao.InexactDate.fromstring('2010')
        assert ied.year() == 2010 and ied.month() is None and ied.day() is None
        ied = dao.InexactDate.fromstring('2.2010')
        assert ied.year() == 2010 and ied.month() == 2 and ied.day() is None
        ied = dao.InexactDate.fromstring('12.06.2014')
        assert ied.year() == 2014 and ied.month() == 6 and ied.day() == 12
        ied = dao.InexactDate.fromstring('')
        assert ied.year() is None and ied.month() is None and ied.day() is None

        with pytest.raises(ValueError):
            dao.InexactDate.fromstring('some wrong input')

        with pytest.raises(ValueError):
            dao.InexactDate.fromstring('10..2010')

        with pytest.raises(ValueError):
            dao.InexactDate.fromstring('29.2.2015')

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


class TestSummit():

    @pytest.fixture
    def summit1(self):
        summit1 = dao.Summit()
        summit1.id = 1
        summit1.name = "Small Yamantau"
        summit1.height = 1519
        summit1.name_alt = "Kuyantau"
        summit1.coordinates = (53.1111, 58.2222)
        summit1.ridge = 'Yamantau'
        summit1.rid = 1
        summit1.color = 'aaaaaa'
        summit1.climbed = False
        summit1.main = False
        return summit1

    @pytest.fixture
    def summit2(self):
        summit2 = dao.Summit()
        summit2.name = ''
        summit2.height = 1111
        summit2.name_alt = ''
        return summit2

    def test_format_name_when_name_exists(self, summit1):
        assert summit1.format_name() == "Small Yamantau"

    def test_format_name_when_only_height(self, summit2):
        assert summit2.format_name() == "1111"

    def test_togeojson(self, summit1):
        assert summit1.to_geojson() ==  \
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

    def test_format_coordinates(self, summit1):
        assert summit1.format_coordinates() == \
            u"53.1111 58.2222 (53\u00b06'39.96''N 58\u00b013'19.92''E)"


class TestSummitDao():

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

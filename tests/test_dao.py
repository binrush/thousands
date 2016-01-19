# coding: utf8
from thousands import dao
from mock import MagicMock
import pytest
import thousands
import tempfile


class TestInexactDate():
    def test_init(self):
        ied = dao.InexactDate(2010, 10, 10)
        assert ied.year == 2010
        assert ied.month == 10
        assert ied.day == 10

        wrong_inputs = [(2010, 13), (2015, 2, 29)]
        for i in wrong_inputs:
            with pytest.raises(ValueError):
                dao.InexactDate(*i)

    def test_fromstring(self):
        correct_cases = [('2010', (2010, )),
                         ('2.2010', (2010, 2)),
                         ('12.06.2014', (2014, 6, 12)),
                         ('', ())]
        for c in correct_cases:
            ied = dao.InexactDate.fromstring(c[0])
            assert ied == dao.InexactDate(*c[1])

        incorrect_cases = ['some wrong input', '10..2010', '29.2.2015']
        for c in incorrect_cases:
            with pytest.raises(ValueError):
                dao.InexactDate.fromstring(c)

    def test_fromdict(self):
        cases = [({'year': 2010, 'month': 10, 'day': 10}, (2010, 10, 10)),
                 ({'year': 2010, 'month': 10, 'day': None}, (2010, 10)),
                 ({'year': 2010}, (2010, )),
                 ({}, ())]
        for c in cases:
            ied = dao.InexactDate.fromdict(c[0])
            assert ied == dao.InexactDate(*c[1])

    def test_format(self):
        cases = [((2010, ), u'2010'),
                 ((2010, 10), u'Октябрь 2010'),
                 ((2010, 10, 10), u'10 Октября 2010'),
                 ((), u'')]
        for c in cases:
            ied = dao.InexactDate(*c[0])
            assert ied.format() == c[1]


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
        assert [v.number for v in res] == [3, 1, 2]


class TestDatabaseImagesDao():

    @pytest.fixture
    def idao(self):
        return dao.DatabaseImagesDao(thousands.pool)

    def test_create(self, idao):
        idao.create('1.jpg', '\xff\xaa\xbb')
        img = idao.get('1.jpg')
        assert img.payload.read() == '\xff\xaa\xbb'
        idao.delete('1.jpg')

    def test_create_exsisting(self, idao):
        idao.create('2.jpg', '\xaa\xbb\xcc')
        idao.create('2.jpg', '\xdd\xee\xff')
        assert idao.get('2.jpg').payload.read() == \
            '\xaa\xbb\xcc'
        idao.delete('2.jpg')

    def test_delete(self, idao):
        idao.create('3.jpg', '\x00\x11\x22')
        idao.delete('3.jpg')
        assert idao.get('3.jpg') is None


class TestFilesystemImagesDao(TestDatabaseImagesDao):

    @pytest.fixture
    def idao(self):
        return dao.FilesystemImagesDao(tempfile.gettempdir())

# coding: utf-8
import pytest
from thousands import model


class TestInexactDate():
    def test_init(self):
        ied = model.InexactDate(2010, 10, 10)
        assert ied.year == 2010
        assert ied.month == 10
        assert ied.day == 10

        wrong_inputs = [(2010, 13), (2015, 2, 29)]
        for i in wrong_inputs:
            with pytest.raises(ValueError):
                model.InexactDate(*i)

    def test_fromstring(self):
        correct_cases = [('2010', (2010, )),
                         ('2.2010', (2010, 2)),
                         ('12.06.2014', (2014, 6, 12)),
                         ('', ())]
        for c in correct_cases:
            ied = model.InexactDate.fromstring(c[0])
            assert ied == model.InexactDate(*c[1])

        incorrect_cases = ['some wrong input', '10..2010', '29.2.2015']
        for c in incorrect_cases:
            with pytest.raises(ValueError):
                model.InexactDate.fromstring(c)

    def test_fromdict(self):
        cases = [({'year': 2010, 'month': 10, 'day': 10}, (2010, 10, 10)),
                 ({'year': 2010, 'month': 10, 'day': None}, (2010, 10)),
                 ({'year': 2010}, (2010, )),
                 ({}, ())]
        for c in cases:
            ied = model.InexactDate.fromdict(c[0])
            assert ied == model.InexactDate(*c[1])

    def test_format(self):
        cases = [((2010, ), u'2010'),
                 ((2010, 10), u'Октябрь 2010'),
                 ((2010, 10, 10), u'10 Октября 2010'),
                 ((), u'')]
        for c in cases:
            ied = model.InexactDate(*c[0])
            assert ied.format() == c[1]


class TestPoint():
    @pytest.fixture
    def point(self):
        return model.Point(53.1111, 58.2222)

    def test_format(self, point):
        assert point.format() == \
            u"53.1111 58.2222 (53\u00b06'39.96''N 58\u00b013'19.92''E)"


class TestSummit():

    @pytest.fixture
    def summit1(self):
        summit1 = model.Summit()
        summit1.id = 'small_yamantau'
        summit1.name = "Small Yamantau"
        summit1.height = 1519
        summit1.name_alt = "Kuyantau"
        summit1.coordinates = (53.1111, 58.2222)
        summit1.ridge = 'Yamantau'
        summit1.ridge_id = 'yamantau'
        summit1.color = 'aaaaaa'
        summit1.climbed = False
        summit1.main = False
        summit1.has_image = False
        return summit1

    @pytest.fixture
    def summit2(self):
        summit2 = model.Summit()
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
                 'ridge_id': 'yamantau',
                 'name': 'Small Yamantau',
                 'color': 'aaaaaa',
                 'climbed': False,
                 'main': False,
                 'has_image': False,
                 'height': 1519
                 },
             'id': 'small_yamantau'}

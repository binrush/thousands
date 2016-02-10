# coding: utf8
from thousands import dao
from thousands import model
import mock
import pytest
import thousands
import tempfile


@pytest.fixture(scope='module', autouse=True)
def prepare_database(request):
    conn = thousands.pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(u"DELETE FROM images")
        conn.commit()
    finally:
        thousands.pool.putconn(conn)

    def cleanup():
        pass

    request.addfinalizer(cleanup)


def test_sql_point_adapter():
    conn = thousands.pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT '(1, 2)'::point")
        point = cur.fetchone()[0]
        assert type(point) == model.Point
        assert point == model.Point(1, 2)
        point = model.Point(2, 1)
        cur.execute("SELECT '(2, 1)'::point ~= %s", (point, ))
        assert cur.fetchone()[0]
    finally:
        thousands.pool.putconn(conn)


class TestSummitDao():

    def test_rate_by_field(self):
        sd = dao.SummitsDao(mock.MagicMock(), mock.MagicMock())
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


class TestImage():

    def test_resize(self):
        cases = (
            ((50, 50), (100, 100), (50, 50)),
            ((50, None), (100, 200), (50, 100)),
            ((None, 50), (100, 200), (25, 50)),
            ((50, None), (200, 100), (50, 25)),
            ((200, None), (700, 700), (200, 200)))
        for c in cases:
            assert model.Image.resize(c[0], c[1]) == c[2]

        with pytest.raises(model.ModelException):
            model.Image.resize((None, None), (50, 50))


class TestDatabaseImagesDao():

    @pytest.fixture
    def idao(self):
        return dao.DatabaseImagesDao(thousands.pool)

    def test_create(self, idao):
        idao.create(model.Image('1.jpg', '\xff\xaa\xbb'))
        img = idao.get('1.jpg')
        assert img.payload == '\xff\xaa\xbb'
        idao.delete('1.jpg')

    def test_delete(self, idao):
        idao.create(model.Image('3.jpg', '\x00\x11\x22'))
        idao.delete('3.jpg')
        assert idao.get('3.jpg') is None


class TestFilesystemImagesDao(TestDatabaseImagesDao):

    @pytest.fixture
    def idao(self):
        return dao.FilesystemImagesDao(tempfile.gettempdir())

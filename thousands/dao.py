# coding: utf-8
from contextlib import contextmanager
import psycopg2.extras
from flask.ext.login import UserMixin
import datetime

AUTH_SRC_VK = 1
AUTH_SRC_SU = 2


class ModelException(Exception):
    pass


class InexactDate(tuple):

    def __new__(cls, *args):

        if len(args) > 3:
            raise TypeError("InexactDate() takes at most 3 arguments, {} given"
                            .format(len(args)))

        if len(args) == 3:
            datetime.date(args[0], args[1], args[2])
        elif len(args) == 2:
            datetime.date(args[0], args[1], 1)
        elif len(args) == 1:
            datetime.date(args[0], 1, 1)

        return tuple.__new__(cls, args)

    @classmethod
    def fromdate(cls, date):
        return cls(date.year, date.month, date.day)

    @classmethod
    def fromstring(cls, data):
        if not data:
            return cls()
        try:
            if len(data) == 4:
                return cls(int(data))
            else:
                return cls(*(reversed([int(f) for f in data.split('.')])))

        except (ValueError, TypeError) as e:
            raise ValueError("Wrong inexact date format: " + data, e)

    @classmethod
    def fromdict(cls, d):
        return InexactDate(*(
            [v for v in (d['year'], d['month'], d['day']) if v is not None]))

    def format(self):
        months_genitive = [
            u'Января', u'Февраля', u'Марта', u'Апреля', u'Мая', u'Июня',
            u'Июля', u'Августа', u'Сентября', u'Октября', u'Ноября',
            u'Декабря']
        months = [
            u'Январь', u'Февраль', u'Март', u'Апрель', u'Май', u'Июнь',
            u'Июль', u'Август', u'Сентябрь', u'Октябрь', u'Ноябрь',
            u'Декабрь']

        if len(self) == 3:
            return u'{} {} {}'.format(self[2],
                                      months_genitive[self[1] - 1],
                                      self[0])
        elif len(self) == 2:
            return u'{} {}'.format(months[self[1]-1], self[0])
        else:
            return unicode(self[0])

    def year(self):
        if len(self) > 0:
            return self[0]
        else:
            return None

    def month(self):
        if len(self) > 1:
            return self[1]
        else:
            return None

    def day(self):
        if len(self) > 2:
            return self[2]
        else:
            return None


class Dao(object):
    pool = None

    def __init__(self, pool):
        self.pool = pool

    @contextmanager
    def get_cursor(self):
        conn = self.pool.getconn()
        conn.autocommit = True
        try:
            yield conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        finally:
            self.pool.putconn(conn)


class Summit(object):

    def __to_mins_secs(self, value):
        deg = int(value)
        mins = (value - deg)*60
        secs = (mins - int(mins))*60
        return u"{}{}{}'{}''".format(deg, u'\u00b0', int(mins), secs)

    def format_name(self):
        return self.name if self.name else str(self.height)

    def format_coordinates(self):
        return u'{} {} ({}{} {}{})'.format(
            self.coordinates[0],
            self.coordinates[1],
            self.__to_mins_secs(self.coordinates[0]),
            'N' if self.coordinates[0] >= 0 else 'S',
            self.__to_mins_secs(self.coordinates[1]),
            'E' if self.coordinates[1] >= 0 else 'W')

    def to_geojson(self):
        ret = {'type': 'Feature',
               'geometry': {"type": "Point"},
               'properties': {}}
        ret['id'] = self.id
        ret['geometry']['coordinates'] = \
            [self.coordinates[1], self.coordinates[0]]
        ret['properties']['height'] = self.height
        ret['properties']['name'] = self.format_name()
        ret['properties']['ridge'] = self.ridge
        ret['properties']['color'] = self.color
        ret['properties']['climbed'] = self.climbed
        ret['properties']['main'] = self.main

        return ret


class SummitsDao(Dao):

    def __row2summit(self, row):
            s = Summit()
            for k in ['id', 'name', 'name_alt', 'height',
                      'description', 'interpretation',
                      'ridge', 'rid', 'color', 'climbed', 'main', 'climbers']:
                if k in row:
                    setattr(s, k, row[k])
            s.coordinates = (row['lat'], row['lng'])
            return s

    def __rate_by_field(self, summits, field):
            index = \
                [elem[0] for elem in sorted(enumerate(summits),
                                            key=lambda f: getattr(f[1], field),
                                            reverse=True)]
            i = 0
            for pos in index:
                summits[pos].number = i + 1
                i += 1
            return summits

    def get_all(self, user_id=None, sort='ridge'):

        if sort == 'height':
            order = "ORDER BY s.height DESC"
        elif sort == 'name':
            order = "ORDER BY s.name, s.name_alt"
        elif sort == 'climbers':
            order = "ORDER BY climbers DESC"
        else:
            order = "ORDER BY r.name, s.lat DESC"

        query = """
        SELECT s.id, s.name, s.name_alt,
                s.height, s.lng, s.lat, r.name AS ridge, r.color,
                count(c.user_id) AS climbers,
            EXISTS (
                SELECT * FROM climbs
                WHERE summit_id=s.id AND user_id=%s
            ) AS climbed,
            EXISTS (
                SELECT * FROM
                    (SELECT rid, max(height) AS maxheight
                        FROM summits WHERE rid=s.rid GROUP BY rid) as smtsg
                    INNER JOIN summits smts
                    ON smtsg.rid=smts.rid AND smts.height=smtsg.maxheight
                    WHERE id=s.id
            ) AS main
        FROM summits s
        LEFT JOIN ridges r ON s.rid=r.id
        LEFT JOIN climbs c ON c.summit_id = s.id
        GROUP BY s.id, s.name, s.name_alt, r.name, r.color """ + order

        with self.get_cursor() as cur:
            cur.execute(query, (user_id, ))
            return self.__rate_by_field(map(self.__row2summit, cur), 'height')

    def get_ridges(self):
        with self.get_cursor() as cur:
            cur.execute("SELECT id, name FROM ridges ORDER BY name")
            return [{"id": row['id'], "name": row['name']} for row in cur]

    def get(self, sid):
        with self.get_cursor() as cur:
            cur.execute(
                """SELECT s.id, s.name, name_alt, height,
                          interpretation, s.description, rid,
                          r.name AS ridge, lng, lat
                   FROM summits s LEFT JOIN ridges r
                   ON s.rid = r.id
                   WHERE s.id=%s""", (sid, ))
            if cur.rowcount < 1:
                return None

            return self.__row2summit(cur.fetchone())

    def create(self, summit):
        with self.get_cursor() as cur:
            query = """INSERT INTO summits
                (name, name_alt, height, description, rid, lat, lng) VALUES
                (%(name)s, %(name_alt)s, %(height)s,
                %(description)s, %(rid)s, round(%(lat)s, 6), round(%(lng)s, 6))
                RETURNING id"""
            cur.execute(query, {
                'name': summit.name,
                'name_alt': summit.name_alt,
                'height': summit.height,
                'description': summit.description,
                'rid': summit.rid,
                'lat': summit.coordinates[0],
                'lng': summit.coordinates[1]})
            return cur.fetchone()['id']

    def update(self, summit):
        with self.get_cursor() as cur:
            query = """UPDATE summits SET
                name=%(name)s, name_alt=%(name_alt)s, height=%(height)s,
                description=%(description)s, interpretation=%(interpretation)s,
                rid=%(rid)s, lat=round(%(lat)s, 6), lng=round(%(lng)s, 6)
                WHERE id=%(id)s"""
            cur.execute(query, {
                'name': summit.name,
                'name_alt': summit.name_alt,
                'height': summit.height,
                'description': summit.description,
                'interpretation': summit.interpretation,
                'rid': summit.rid,
                'lat': summit.coordinates[0],
                'lng': summit.coordinates[1],
                'id': summit.id})
            return summit

    def delete(self, summit_id):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM summits WHERE id=%s", (summit_id, ))


class User(UserMixin):

    __auth_sources = {
        AUTH_SRC_VK:
            u'<a href="https://vk.com/id{}" target="_blank">' +
            u'Профиль ВКонтакте</a>',
        AUTH_SRC_SU:
            u'<a href="http://www.southural.ru/authors/{}" target="_blank">' +
            u'Профиль на southural.ru</a>'
    }

    def social_link(self):
        return self.__auth_sources[self.src].format(self.oauth_id)


class UsersDao(Dao):

    def _fromrow(self, row):
        user = User()
        for k in row.keys():
            setattr(user, k, row[k])
        return user

    def get(self, oauth_id, src):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE oauth_id=%s AND src=%s",
                        (oauth_id, src))
            if cur.rowcount < 1:
                return None
            return self._fromrow(cur.fetchone())

    def get_by_id(self, id_):
        try:
            user_id = int(id_)
        except ValueError:
            return None
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id, ))
            if cur.rowcount < 1:
                return None
            return self._fromrow(cur.fetchone())

    def create(self, user):
        sql = """INSERT INTO users (src, oauth_id, name, image_id, preview_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        with self.get_cursor() as cur:
            cur.execute(sql, (
                user.src,
                user.oauth_id,
                user.name,
                user.image_id,
                user.preview_id))
            if cur.rowcount < 1:
                return None
            return cur.fetchone()['id']


class Image(object):
    pass


class ImagesDao(Dao):

    def create(self, data, fmt):
        sql = "INSERT INTO images (type, payload) VALUES (%s, %s) RETURNING id"
        with self.get_cursor() as cur:
            cur.execute(sql, (fmt, psycopg2.Binary(data)))
            if cur.rowcount < 1:
                return None
            else:
                return cur.fetchone()['id']

    def get(self, image_id):
        sql = "SELECT * FROM images WHERE id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (image_id, ))
            if cur.rowcount < 1:
                return None
            else:
                row = cur.fetchone()
                img = Image()
                img.id = row['id']
                img.type = row['type']
                img.payload = row['payload']
                return img


class Climb(object):
    pass


class ClimbsDao(Dao):

    def climbers(self, summit_id):
        climbers = []
        sql = """SELECT
                    year,
                    month,
                    day,
                    comment,
                    users.id,
                    users.name,
                    users.preview_id
                FROM users LEFT JOIN climbs ON climbs.user_id=users.id
                LEFT JOIN summits ON climbs.summit_id=summits.id
                WHERE climbs.summit_id=%s
                ORDER BY year, month, day;"""
        with self.get_cursor() as cur:
            cur.execute(sql, (summit_id, ))
            for row in cur:
                u = User()
                u.id = row['id']
                u.name = row['name']
                u.preview_id = row['preview_id']
                climbers.append(
                    {'user': u, 'date': InexactDate.fromdict(row),
                     'comment': row['comment']})
        return climbers

    def climbed(self, user_id):
        climbed = []
        sql = """SELECT
                    year, month, day, comment,
                    summits.id, summits.name, height, ridges.name AS ridge
                FROM ridges LEFT JOIN summits ON ridges.id=summits.rid
                LEFT JOIN climbs ON summits.id=climbs.summit_id
                WHERE climbs.user_id=%s
                ORDER BY year, month, day"""
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, ))
            for row in cur:
                s = Summit()
                s.name = row['name']
                s.ridge = row['ridge']
                s.id = row['id']
                s.height = row['height']
                climbed.append(
                    {'summit': s,
                     'date': InexactDate.fromdict(row),
                     'comment': row['comment']})
            return climbed

    def top(self):
        users = []
        sql = """SELECT users.id, users.name, users.preview_id, COUNT(climbs.*) AS climbs
                FROM users LEFT JOIN climbs ON users.id=climbs.user_id
                GROUP BY users.id, users.name, users.preview_id
                ORDER BY climbs DESC
        """
        with self.get_cursor() as cur:
            cur.execute(sql)
            for row in cur:
                u = User()
                u.id = row['id']
                u.name = row['name']
                u.preview_id = row['preview_id']
                u.climbs = row['climbs']
                users.append(u)
        return users

    def get(self, user_id, summit_id):
        sql = "SELECT year, month, day, comment" + \
            " FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))
            if cur.rowcount < 1:
                return None
            row = cur.fetchone()
            climb = Climb()
            climb.date = \
                InexactDate.fromdict(row)
            climb.comment = row['comment']
        return climb

    def create(self, user_id, summit_id, date=None, comment=None):
        sql = "INSERT INTO climbs (user_id, summit_id, comment, year, month, day)" + \
            " VALUES (%s, %s, %s, %s, %s, %s)"
        with self.get_cursor() as cur:
            cur.execute(
                sql,
                (user_id, summit_id, comment,
                 date.year(), date.month(), date.day()))

    def update(self, user_id, summit_id, date=None, comment=None):
        sql = "UPDATE climbs SET year=%s, month=%s, day=%s, comment=%s" + \
            " WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(
                sql,
                (date.year(), date.month(), date.day(),
                 comment, user_id, summit_id))

    def delete(self, user_id, summit_id):
        sql = "DELETE FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))

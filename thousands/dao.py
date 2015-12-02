# coding: utf-8
from contextlib import contextmanager
import psycopg2.extras
from flask.ext.login import UserMixin
import datetime


class InexactDate(object):
    def __init__(self, year, month=None, day=None):
        if day is not None:
            if month is None:
                raise ValueError("Month cannot be None if day is not")
            else:
                # validate
                datetime.date(year, month, day)
        elif month is not None:
            if month < 1 or month > 12:
                raise ValueError("Month should be between 1 and 12")

        self.year, self.month, self.day = \
            year, month, day

    @classmethod
    def fromdate(cls, date):
        return cls(date.year, date.month, date.day)

    @classmethod
    def fromstring(cls, data):
        try:
            if len(data) == 4:
                year = int(data)
                month = None
                day = None
            else:
                fields = [int(f) for f in data.split('.')]
                if len(fields) == 2:
                    month, year = fields
                    day = None
                elif len(fields) == 3:
                    d = datetime.date(*(list(reversed(fields))))
                    year, month, day = d.year, d.month, d.day
                else:
                    raise ValueError("Wrong inexact date format: " + data)
        except ValueError, e:
            raise ValueError("Wrong inexact date format: " + data, e)
        return cls(year, month, day)

    def format(self):
        months_genitive = [
            u'Января',
            u'Февраля',
            u'Марта',
            u'Апреля',
            u'Мая',
            u'Июня',
            u'Июля',
            u'Августа',
            u'Сентября',
            u'Октября',
            u'Ноября',
            u'Декабря']
        months = [
            u'Январь',
            u'Февраль',
            u'Март',
            u'Апрель',
            u'Май',
            u'Июнь',
            u'Июль',
            u'Август',
            u'Сентябрь',
            u'Октябрь',
            u'Ноябрь',
            u'Декабрь']
        if self.day is not None:
            return u'{} {} {}'.format(self.day,
                                      months_genitive[self.month - 1],
                                      self.year)
        elif self.month is not None:
            return u'{} {}'.format(months[self.month-1], self.year)
        else:
            return str(self.year)

    def tuple(self):
        return (self.year, self.month, self.day)

    def __cmp__(self, other):
        return cmp(self.tuple(), other.tuple())


class ModelException(Exception):
    pass


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

    def to_mins_secs(self, value):
        deg = int(value)
        mins = (value - deg)*60
        secs = (mins - int(mins))*60
        return u"{}{}{}'{}''".format(deg, u'\u00b0', int(mins), secs)

    def format_name(self):
        return self.name if self.name else str(self.height)

    def format_name_alt(self):
        return '(' + self.name_alt + ')' if self.name_alt else ''

    def format_coordinates(self):
        return u'{} {} ({}{} {}{})'.format(
            self.coordinates[0],
            self.coordinates[1],
            self.to_mins_secs(self.coordinates[0]),
            'N' if self.coordinates[0] >= 0 else 'S',
            self.to_mins_secs(self.coordinates[1]),
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
        ret['properties']['name_alt'] = self.format_name_alt()
        ret['properties']['ridge'] = self.ridge
        ret['properties']['color'] = self.color
        ret['properties']['climbed'] = self.climbed
        ret['properties']['main'] = self.main

        return ret


class Image(object):
    pass


class Climb(object):
    pass


class SummitsDao(Dao):

    def get_all(self, user_id=None, sort='ridge'):
        def row2summit(row):
            s = Summit()
            for k in ['id', 'name', 'name_alt', 'height',
                      'ridge', 'color', 'climbed', 'main', 'climbers']:
                setattr(s, k, row[k])
            s.coordinates = (row['lat'], row['lng'])
            return s

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
            summits = map(row2summit, cur)
            sortkey = lambda f: f[1].height
            index = [elem[0] for elem in sorted(enumerate(summits),
                                                key=sortkey,
                                                reverse=True)]
            i = 0
            for pos in index:
                summits[pos].number = i + 1
                i += 1
            return summits

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
            row = cur.fetchone()
            summit = Summit()
            for k in ['id', 'name', 'name_alt', 'height',
                      'interpretation', 'description', 'rid', 'ridge']:
                setattr(summit, k, row[k])
            summit.coordinates = (row['lat'], row['lng'])
            return summit

    def create(self, summit):
        with self.get_cursor() as cur:
            query = """INSERT INTO summits
                (name, name_alt, height, description, rid, lat, lng) VALUES
                (%(name)s, %(name_alt)s, %(height)s,
                %(description)s, %(rid)s, round(%(lat)s, 6), round(%(lng)s, 6))
                RETURNING id"""
            print query
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


class UsersDao(Dao):

    def _fromrow(self, row):
        user = UserMixin()
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
        sql = """INSERT INTO users (src, oauth_id, name, image_id, location, preview_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        with self.get_cursor() as cur:
            cur.execute(sql, (
                user.src,
                user.oauth_id,
                user.name,
                user.image_id,
                user.location,
                user.preview_id))
            if cur.rowcount < 1:
                return None
            return cur.fetchone()['id']

    def update(self, user_id, user):
        sql = """UPDATE users SET name=%s, location=%s, about=%s
            WHERE id=%s"""
        with self.get_cursor() as cur:
            cur.execute(sql, (user.name, user.location, user.about, user_id))
            if cur.rowcount < 1:
                raise ModelException("User not fount while updating")


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
                u = UserMixin()
                u.id = row['id']
                u.name = row['name']
                u.preview_id = row['preview_id']
                if row['year'] is not None:
                    date = InexactDate(row['year'], row['month'], row['day'])
                else:
                    date = None
                climbers.append(
                    {'user': u, 'date': date, 'comment': row['comment']})
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
                if row['year'] is not None:
                    date = InexactDate(row['year'], row['month'], row['day'])
                else:
                    date = None
                climbed.append(
                    {'summit': s,
                     'date': date,
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
                u = UserMixin()
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
            climb.date = InexactDate(row['year'], row['month'], row['day'])
            climb.comment = row['comment']
        return climb

    def create(self, user_id, summit_id, date=None, comment=None):
        sql = "INSERT INTO climbs (user_id, summit_id, comment, year, month, day)" + \
            " VALUES (%s, %s, %s, %s, %s, %s)"
        with self.get_cursor() as cur:
            cur.execute(
                sql,
                (user_id, summit_id, comment, date.year, date.month, date.day))

    def update(self, user_id, summit_id, date=None, comment=None):
        sql = "UPDATE climbs SET year=%s, month=%s, day=%s, comment=%s" + \
            " WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(
                sql,
                (date.year, date.month, date.day, comment, user_id, summit_id))

    def delete(self, user_id, summit_id):
        sql = "DELETE FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))

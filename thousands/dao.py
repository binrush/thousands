# coding: utf-8
from contextlib import contextmanager
import psycopg2.extras
import os
import logging
from model import (Summit, SummitImage, InexactDate, User, Image)

logger = logging.getLogger(__name__)


class DaoException(Exception):
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


class SummitsDao(Dao):

    def __row2summit(self, row):
            s = Summit()
            for k in ['id', 'name', 'name_alt', 'height', 'number',
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

    def __get_many(self, query, params):
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return self.__rate_by_field(map(self.__row2summit, cur), 'height')

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

        return self.__get_many(query, (user_id, ))

    def get_by_ridge(self, rids, user_id=None):

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
        WHERE rid IN %s
        GROUP BY s.id, s.name, s.name_alt, r.name, r.color
        ORDER BY r.name, s.lat DESC"""

        return self.__get_many(query, (user_id, tuple(rids)))

    def get_ridges(self):
        with self.get_cursor() as cur:
            cur.execute("SELECT id, name FROM ridges ORDER BY name")
            return [{"id": row['id'], "name": row['name']} for row in cur]

    def get(self, sid, images=False):
        with self.get_cursor() as cur:
            cur.execute(
                """SELECT s.id, s.name, name_alt, height,
                          interpretation, s.description, rid,
                          r.name AS ridge, lng, lat,
                          (SELECT COUNT(*) FROM summits
                              WHERE height >= s.height ) AS number,
                          (SELECT MAX(height)=s.height FROM summits
                              WHERE rid=s.rid) AS main
                   FROM summits s LEFT JOIN ridges r
                   ON s.rid = r.id
                   WHERE s.id=%s""", (sid, ))
            if cur.rowcount < 1:
                return None

            summit = self.__row2summit(cur.fetchone())
            summit.images = []

            if images:
                cur.execute("SELECT image, summit_id, preview, comment " +
                            " FROM summits_images " +
                            " WHERE summit_id=%s ORDER BY main", (sid, ))
                for row in cur:
                    summit.images.append(SummitImage(**row))

            return summit

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

    def get_image(self, image_id):
        query = "SELECT * FROM summits_images WHERE image=%s"
        with self.get_cursor() as cur:
            cur.execute(query, (image_id, ))
            if cur.rowcount == 1:
                row = cur.fetchone()
                return SummitImage(**row)

    def create_image(self, summit_id, image, preview, comment):
        query = """INSERT INTO summits_images (summit_id, image, preview, comment)
                VALUES (%s, %s, %s, %s)"""
        with self.get_cursor() as cur:
            cur.execute(query, (summit_id, image, preview, comment))

    def update_image(self, image_id, comment):
        """
            Only updating of comment makes sense
        """
        with self.get_cursor() as cur:
            cur.execute("UPDATE summits_images SET comment=%s WHERE image=%s",
                        (comment, image_id))

    def delete_image(self, image_id):
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM summits_images WHERE image=%s",
                        (image_id, ))


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
        sql = """INSERT INTO users (src, oauth_id, name, image, preview)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        with self.get_cursor() as cur:
            cur.execute(sql, (
                user.src,
                user.oauth_id,
                user.name,
                user.image,
                user.preview))
            if cur.rowcount < 1:
                return None
            return cur.fetchone()['id']

    def update(self, user):
        sql = """UPDATE users SET name=%s, image=%s, preview=%s
              WHERE id=%s"""
        with self.get_cursor() as cur:
            cur.execute(sql, (
                user.name,
                user.image,
                user.preview,
                user.get_id()))


class DatabaseImagesDao(Dao):

    def create(self, image):
        logger.debug('Saving image %s to database, len=%s',
                     image.name, len(image.payload))
        sql = "INSERT INTO images (name, payload) " + \
              "VALUES (%s, %s)"
        with self.get_cursor() as cur:
            cur.execute(sql, (image.name, psycopg2.Binary(image.payload)))

    def get(self, image_id):
        sql = "SELECT * FROM images WHERE name=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (image_id, ))
            if cur.rowcount < 1:
                return None
            else:
                row = cur.fetchone()
                img = Image(row['name'], bytes(row['payload']))
                return img

    def delete(self, image_id):
        sql = "DELETE FROM images WHERE name=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (image_id, ))


class FilesystemImagesDao():

    def __init__(self, directory):
        if not os.path.isdir(directory):
            raise DaoException('Not a directory: ' + directory)
        self.directory = directory

    def __path(self, filename):
        return os.path.join(self.directory, filename)

    def create(self, img):
        with open(os.path.join(self.directory, img.name), 'w') as fp:
            fp.write(img.payload)

    def get(self, image_id):
        try:
            return Image(
                image_id,
                open(os.path.join(self.directory, image_id)).read())
        except IOError:
            return None

    def delete(self, image_id):
        path = os.path.join(self.directory, image_id)
        if os.path.exists(path):
            os.unlink(path)


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
                    users.preview
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
                u.preview = row['preview']
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
        sql = """SELECT users.id, users.name, users.preview, COUNT(climbs.*) AS climbs
                FROM users LEFT JOIN climbs ON users.id=climbs.user_id
                GROUP BY users.id, users.name, users.preview
                ORDER BY climbs DESC
        """
        with self.get_cursor() as cur:
            cur.execute(sql)
            for row in cur:
                u = User()
                u.id = row['id']
                u.name = row['name']
                u.preview = row['preview']
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
                 date.year, date.month, date.day))

    def update(self, user_id, summit_id, date=None, comment=None):
        sql = "UPDATE climbs SET year=%s, month=%s, day=%s, comment=%s" + \
            " WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(
                sql,
                (date.year, date.month, date.day,
                 comment, user_id, summit_id))

    def delete(self, user_id, summit_id):
        sql = "DELETE FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))

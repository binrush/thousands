from contextlib import contextmanager
import psycopg2.extras 
from flask.ext.login import UserMixin

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

    def format_name(self):
        return self.name if self.name else str(self.height)

    def format_name_alt(self):
        return '(' + self.name_alt + ')' if self.name_alt else ''
    
    def to_geojson(self):
        ret = { 'type': 'Feature', 'geometry': { "type": "Point" }, 'properties': {} }
        ret['id'] = self.id
        ret['geometry']['coordinates'] = [ self.coordinates[1], self.coordinates[0]]
        ret['properties']['height'] = self.height
        ret['properties']['name'] = self.format_name()
        ret['properties']['name_alt'] = self.format_name_alt()
        ret['properties']['ridge'] = self.ridge
        ret['properties']['color'] = self.color
        ret['properties']['climbed'] = self.climbed

        return ret

class Image(object):
    pass

class Climb(object):
    pass

class SummitsDao(Dao):

    def get_all(self, user_id=None, orderByHeight=False):
        def row2summit(row):
            s = Summit()
            for k in [ 'id', 'name', 'name_alt', 'height', 'ridge', 'color', 'climbed' ]:
                setattr(s, k, row[k])
            s.coordinates = ( row['lat'], row['lng'] )
            return s
        with self.get_cursor() as cur:
            if orderByHeight:
                order = "ORDER BY s.height DESC"
            else:
                order = "ORDER BY r.name, s.lat DESC"
            cur.execute(
                """SELECT s.id, s.name, s.name_alt, 
                    s.height, s.lng, s.lat, r.name AS ridge, r.color,
                    EXISTS (
                        SELECT * FROM climbs 
                        WHERE summit_id=s.id AND user_id=%s) AS climbed
                FROM summits s LEFT JOIN ridges r ON s.rid=r.id """ + order, (user_id, ))
            summits = map(row2summit, cur)
            sortkey = lambda f: f[1].height
            index = [ elem[0] for elem in sorted(enumerate(summits), key=sortkey, reverse=True) ]
            i = 0
            for pos in index:
                summits[pos].number = i + 1
                i += 1
            #return { 'type': 'FeatureCollection', 'features': features }
            return summits
    
    def get_ridges(self):
        with self.get_cursor() as cur:
            cur.execute("SELECT id, name FROM ridges ORDER BY name")
            return [ {"id": row['id'], "name": row['name']} for row in cur ]
    
    def get(self, sid):
        with self.get_cursor() as cur:
            cur.execute(
                    """SELECT s.id, s.name, name_alt, height, interpretation, s.description, rid, r.name AS ridge, lng, lat
                    FROM summits s LEFT JOIN ridges r
                    ON s.rid = r.id
                    WHERE s.id=%s""", (sid, ))
            if cur.rowcount < 1:
                return None
            row = cur.fetchone()
            #geometry = { 'type': 'Point', 'coordinates': [ row['lng'], row['lat'] ] }
            #properties = {} 
            summit = Summit()
            for k in [ 'id', 'name', 'name_alt', 'height', 'interpretation', 'description', 'rid', 'ridge' ]:
                setattr(summit, k, row[k])
            summit.coordinates = (row['lat'], row['lng'])
            return summit
    
    def create(self, summit):
        with self.get_cursor() as cur:
            query = """INSERT INTO summits
                (name, name_alt, height, description, rid, lat, lng) VALUES
                (%(name)s, %(name_alt)s, %(height)s, %(description)s, %(rid)s, %(lat)s, %(lng)s)
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
                rid=%(rid)s, lat=%(lat)s, lng=%(lng)s
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
        


    def row2feature(self, row):
    
        return ret

class UsersDao(Dao):

    def _fromrow(self, row):
        user = UserMixin()
        for k in row.keys():
            setattr(user, k, row[k])
        return user

    def get(self, oauth_id, src):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE oauth_id=%s AND src=%s", (oauth_id, src))
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
                    ts,
                    comment,
                    users.id,
                    users.name,
                    users.preview_id
                FROM users LEFT JOIN climbs ON climbs.user_id=users.id 
                LEFT JOIN summits ON climbs.summit_id=summits.id
                WHERE climbs.summit_id=%s
                ORDER BY ts;"""
        with self.get_cursor() as cur:
            cur.execute(sql, (summit_id, ))
            for row in cur:
                u = UserMixin()
                u.id = row['id']
                u.name = row['name']
                u.preview_id = row['preview_id']
                climbers.append({ 'user': u, 'date': row['ts'], 'comment': row['comment']})
        return climbers

    def climbed(self, user_id):
        climbed = []
        sql = """SELECT ts, comment, id, name, name_alt, height
                FROM summits LEFT JOIN climbs ON summits.id=climbs.summit_id
                WHERE climbs.user_id=%s
                ORDER BY ts"""
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, ))
            for row in cur:
                s = Summit()
                s.name = row['name']
                s.name_alt = row['name_alt']
                s.id = row['id']
                s.height = row['height']
                climbed.append({ 'summit': s, 'date': row['ts'], 'comment': row['comment'] })
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
        sql = "SELECT ts, comment FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))
            if cur.rowcount < 1:
                return None
            row = cur.fetchone()
            climb = Climb()
            climb.date = row['ts']
            climb.comment = row['comment']
        return climb

    def create(self, user_id, summit_id, date=None, comment=None):
        sql = "INSERT INTO climbs (user_id, summit_id, ts, comment) VALUES (%s, %s, %s, %s)"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id, date, comment))

    def update(self, user_id, summit_id, date=None, comment=None):
        sql = "UPDATE climbs SET ts=%s, comment=%s WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (date, comment, user_id, summit_id))

    def delete(self, user_id, summit_id):
        sql = "DELETE FROM climbs WHERE user_id=%s AND summit_id=%s"
        with self.get_cursor() as cur:
            cur.execute(sql, (user_id, summit_id))

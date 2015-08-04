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
        ret['geometry']['coordinates'] = [ self.lng, self.lat ]
        ret['properties']['height'] = self.height
        ret['properties']['name'] = self.format_name()
        ret['properties']['name_alt'] = self.format_name_alt()
        ret['properties']['ridge'] = self.ridge
        ret['properties']['color'] = self.color

        return ret

class SummitsDao(Dao):

    def get_all(self, user=None, orderByHeight=False):
        with self.get_cursor() as cur:
            if orderByHeight:
                order = "ORDER BY s.height DESC"
            else:
                order = "ORDER BY r.name, s.lat DESC"
            cur.execute(
                """SELECT s.id, s.name, s.name_alt, s.height, s.lng, s.lat, r.name AS ridge, r.color
                FROM summits s LEFT JOIN ridges r ON s.rid=r.id """ + order)
            summits = map(self.row2summit, cur)
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
            for k in row.keys():
                setattr(summit, k, row[k])
            return summit
    
    def create(self, data):
        with get_cursor() as cur:
            query = """INSERT INTO summits
                (name, name_alt, height, description, rid, lat, lng) VALUES
                (%(name)s, %(name_alt)s, %(height)s, %(description)s, %(rid)s, %(lat)s, %(lng)s)
                RETURNING id"""
            cur.execute(query, {
                'name': data['properties']['name'],
                'name_alt': data['properties']['name_alt'],
                'height': data['properties']['height'],
                'description': data['properties']['description'],
                'rid': data['properties']['rid'],
                'lat': data['geometry']['coordinates'][1],
                'lng': data['geometry']['coordinates'][0]})
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
                'lat': summit.lat,
                'lng': summit.lng,
                'id': summit.id})
            return summit
    
    def row2summit(self, row):
        s = Summit()
        for k in row.keys():
            setattr(s, k, row[k])
        return s

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
            cur.execute("SELECT * FROM users WHERE oauth_id='%s' AND src=%s", (oauth_id, src))
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
        sql = """INSERT INTO users (src, oauth_id, name, email, img_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        with self.get_cursor() as cur:
            cur.execute(sql, (user.src, user.oauth_id, user.name, user.email, user.img_id))
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


from contextlib import contextmanager
import psycopg2.extras 

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

    def get_all(self, orderByHeight=False):
        with self.get_cursor() as cur:
            if orderByHeight:
                order = "ORDER BY s.height DESC"
            else:
                order = "ORDER BY r.name, s.lat DESC"
            cur.execute(
                """SELECT s.id, s.name, s.name_alt, s.height, s.lng, s.lat, r.name AS ridge, r.color
                FROM summits s LEFT JOIN ridges r ON s.rid=r.id """ + order)
            features = map(self.row2feature, cur)
            sortkey = lambda f: f[1]['properties']['height']
            index = [ elem[0] for elem in sorted(enumerate(features), key=sortkey, reverse=True) ]
            i = 0
            for pos in index:
                features[pos]['properties']['number'] = i + 1
                i += 1
            return { 'type': 'FeatureCollection', 'features': features }
    
    def get_ridges():
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM ridges ORDER BY name")
            ridges = [ {"id": row['id'], "name": row['name']} for row in cur ]
            return { "ridges": ridges }
    
    def get(sid):
        with get_cursor() as cur:
            cur.execute(
                    """SELECT s.id, s.name, name_alt, height, s.description, rid, r.name AS ridge, lng, lat
                    FROM summits s LEFT JOIN ridges r
                    ON s.rid = r.id
                    WHERE s.id=%s""", (sid, ))
            if cur.rowcount < 1:
                raise ValueError("Incorrect summit id requested")
            row = cur.fetchone()
            geometry = { 'type': 'Point', 'coordinates': [ row['lng'], row['lat'] ] }
            properties = {} 
            for p in ['name', 'name_alt', 'height', 'description', 'rid', 'ridge' ]:
                properties[p] = row[p]
            return { 'type': 'Feature', 'id': row['id'], 'geometry': geometry, 'properties': properties }
    
    def create(data):
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
    
    def update(sid, data):
        with get_cursor() as cur:
            query = """UPDATE summits SET 
                name=%(name)s, name_alt=%(name_alt)s, height=%(height)s, description=%(description)s,
                rid=%(rid)s, lat=%(lat)s, lng=%(lng)s
                WHERE id=%(id)s"""
            cur.execute(query, {
                'name': data['properties']['name'],
                'name_alt': data['properties']['name_alt'],
                'height': data['properties']['height'],
                'description': data['properties']['description'],
                'rid': data['properties']['rid'],
                'lat': data['geometry']['coordinates'][1],
                'lng': data['geometry']['coordinates'][0],
                'id': sid})
            return data['id']
    
    def row2feature(self, row):
        ret = { 'type': 'Feature', 'geometry': { "type": "Point" }, 'properties': {} }
        ret['id'] = row['id']
        ret['geometry']['coordinates'] = [ row['lng'], row['lat'] ]
        ret['properties']['height'] = row['height']
        ret['properties']['name'] = row['name'] if row['name'] else str(row['height'])
        ret['properties']['name_alt'] = row['name_alt']
        ret['properties']['ridge'] = row['ridge']
        ret['properties']['color'] = row['color']
    
        return ret

class UsersDao(Dao):
    
    def get(self, oauth_id, src):
        with self.get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE oauth_id='%s' AND src=%s", (oauth_id, src))
            if cur.rowcount < 1:
                return None
            row = cur.fetchone()
            user = {}
            for k in row.keys():
                user[k] = row[k]
            return user
    
    def create(user):
        fd = urllib.urlopen(user['image'])
        if fd.getcode() == 200:
            img_id = images.store(fd.read(), fd.info().gettype())
        else:
            img_id = None
        
        sql = """INSERT INTO users (src, oauth_id, name, email, img_id, pub)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        with database.get_cursor() as cur:
            cur.execute(sql, (user['src'], user['oauth_id'], user['name'], user['email'], img_id, user['pub']))
            if cur.rowcount < 1:
                return None
            return cur.fetchone()['id']

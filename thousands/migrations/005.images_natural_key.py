from yoyo import step
import hashlib
import mimetypes


def do_step(conn):
    mimetypes.init()
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE images ADD COLUMN name varchar(64)")
        cur.execute("SELECT id, type, payload FROM images")
        for img in cur:
            name = hashlib.sha1(img[2]).hexdigest() + \
                mimetypes.guess_extension(img[1])

            with conn.cursor() as cur_upd:
                cur_upd.execute("UPDATE images SET name=%s WHERE id=%s",
                                (name, img[0]))
        cur.execute("ALTER TABLE users DROP CONSTRAINT users_img_id_fkey")
        cur.execute("ALTER TABLE users DROP CONSTRAINT users_preview_id_fkey")
        cur.execute("ALTER TABLE users ADD COLUMN image varchar(64)")
        cur.execute("ALTER TABLE users ADD COLUMN preview varchar(64)")
        cur.execute("UPDATE users SET image=subquery.name " +
                    "FROM (SELECT id, name FROM images) AS subquery " +
                    "WHERE users.image_id=subquery.id")
        cur.execute("UPDATE users SET preview=subquery.name " +
                    "FROM (SELECT id, name FROM images) AS subquery " +
                    "WHERE users.preview_id=subquery.id")
        cur.execute("ALTER TABLE users DROP COLUMN image_id")
        cur.execute("ALTER TABLE users DROP COLUMN preview_id")
        cur.execute("ALTER TABLE images DROP COLUMN type")
        cur.execute("ALTER TABLE images DROP COLUMN id")
        cur.execute("CREATE TABLE images_temp AS " +
                    "SELECT DISTINCT * FROM images")
        cur.execute("DROP TABLE images")
        cur.execute("ALTER TABLE images_temp RENAME TO images")
        cur.execute("ALTER TABLE images ADD PRIMARY KEY(name)")
        conn.commit()


step(do_step)

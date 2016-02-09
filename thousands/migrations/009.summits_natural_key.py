from yoyo import step
from transliterate import translit


def make_key(name, height):
    if name:
        return translit(name, 'ru', reversed=True) \
            .replace('\'', '') \
            .replace(' ', '_') \
            .lower()
    else:
        return str(height)


def do_step(conn):
    with conn.cursor() as cur:
        cur.execute('ALTER TABLE summits ADD COLUMN id_ varchar(32)')
        cur.execute('ALTER TABLE climbs ADD COLUMN summit_id_ varchar(32)')
        cur.execute('ALTER TABLE summits_images \
                    ADD COLUMN summit_id_ varchar(32)')
        cur.execute('SELECT id, name, height FROM summits')
        for row in cur:
            key_base = key = make_key(row[1], row[2])
            with conn.cursor() as upd_cur:
                index = 1
                while True:
                    upd_cur.execute(
                        'SELECT COUNT(*) FROM summits ' +
                        'WHERE id_=%s', (key, ))
                    if upd_cur.fetchone()[0] == 0:
                        upd_cur.execute(
                            'UPDATE summits SET id_=%s WHERE id=%s',
                            (key, row[0]))
                        upd_cur.execute(
                            'UPDATE climbs SET summit_id_=%s \
                            WHERE summit_id=%s',
                            (key, row[0]))
                        upd_cur.execute(
                            'UPDATE summits_images SET summit_id_=%s \
                            WHERE summit_id=%s',
                            (key, row[0]))
                        break
                    key = key_base + '-' + str(index)
                    index += 1

        cur.execute('ALTER TABLE climbs DROP CONSTRAINT climbs_summit_id_fkey')
        cur.execute('ALTER TABLE climbs DROP COLUMN summit_id')
        cur.execute('ALTER TABLE climbs RENAME COLUMN summit_id_ TO summit_id')

        cur.execute('ALTER TABLE summits_images \
                    DROP CONSTRAINT summits_images_summit_id_fkey')
        cur.execute('ALTER TABLE summits_images DROP COLUMN summit_id')
        cur.execute('ALTER TABLE summits_images \
                    RENAME COLUMN summit_id_ TO summit_id')

        cur.execute('ALTER TABLE summits DROP COLUMN id')
        cur.execute('ALTER TABLE summits RENAME COLUMN id_ TO id')
        cur.execute('ALTER TABLE summits ADD PRIMARY KEY (id)')

        cur.execute('ALTER TABLE climbs ADD PRIMARY KEY ' +
                    '(summit_id, user_id)')
        cur.execute('ALTER TABLE climbs ADD FOREIGN KEY (summit_id) ' +
                    'REFERENCES summits (id)')
        cur.execute('ALTER TABLE summits_images ADD FOREIGN KEY (summit_id) ' +
                    'REFERENCES summits (id)')
        conn.commit()


step(do_step)

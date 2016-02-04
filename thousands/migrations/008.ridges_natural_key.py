from yoyo import step
from transliterate import translit


def make_key(name):
    return translit(name, 'ru', reversed=True) \
        .replace('\'', '') \
        .replace(' ', '_') \
        .lower()


def do_step(conn):
    with conn.cursor() as cur:
        cur.execute('ALTER TABLE ridges ADD COLUMN id_ varchar(32)')
        cur.execute('ALTER TABLE summits ADD COLUMN ridge_id varchar(32)')
        cur.execute('SELECT id, name FROM ridges')
        for row in cur:
            key = make_key(row[1])
            with conn.cursor() as upd_cur:
                upd_cur.execute(
                    'UPDATE ridges SET id_=%s WHERE id=%s', (key, row[0]))
                upd_cur.execute(
                    'UPDATE summits SET ridge_id=%s WHERE rid=%s',
                    (key, row[0]))
        cur.execute('ALTER TABLE summits DROP CONSTRAINT summits_rid_fkey')
        cur.execute('ALTER TABLE summits DROP COLUMN rid')
        cur.execute('ALTER TABLE ridges DROP COLUMN id')
        cur.execute('ALTER TABLE ridges RENAME COLUMN id_ TO id')
        cur.execute('ALTER TABLE ridges ADD PRIMARY KEY (id)')
        cur.execute('ALTER TABLE summits ADD FOREIGN KEY (ridge_id) ' +
                    'REFERENCES ridges (id)')
        conn.commit()


step(do_step)

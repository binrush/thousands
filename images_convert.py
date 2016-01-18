import os
from thousands import (app, pool)


conn = pool.getconn()
try:
    cur = conn.cursor()
    cur.execute("SELECT name, payload FROM images")
    for img in cur:
        with open(os.path.join(app.config['IMAGES_DIR'], img[0]), 'w') as f:
            f.write(bytes(img[1]))
finally:
    pool.putconn(conn)

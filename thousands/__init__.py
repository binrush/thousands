# coding: utf-8
import os
from flask import Flask, g
import psycopg2
import psycopg2.pool
import psycopg2.extensions
import dao
from flask.ext.login import LoginManager
from yoyo import read_migrations
import yoyo.exceptions
import logging


PG_DSN = "dbname = su user = rush"
VK_CLIENT_ID = "4890287"
VK_CLIENT_SECRET = "fake-vk-client-secret"
SU_CLIENT_ID = "thousands"
SU_CLIENT_SECRET = "fake-su-client-secret"

app = Flask(__name__)
app.config.from_object(__name__)
if 'THOUSANDS_CONF' in os.environ:
    app.config.from_envvar('THOUSANDS_CONF')
if 'OPENSHIFT_DATA_DIR' in os.environ:
    app.config.from_pyfile(os.path.join(os.environ['OPENSHIFT_DATA_DIR'],
                           'thousands.conf'))

if app.config['TESTING']:
    print "!!! TESTING MODE"

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
pool = psycopg2.pool.SimpleConnectionPool(1, 10, app.config['PG_DSN'])

migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
console = logging.StreamHandler()
yoyo.migrations.logger.addHandler(console)
conn = pool.getconn()
yoyo.exceptions.register(psycopg2.DatabaseError)
migrations = read_migrations(conn, psycopg2.paramstyle, migrations_dir)
migrations.to_apply().apply()
conn.commit()
pool.putconn(conn)

summits_dao = dao.SummitsDao(pool)
users_dao = dao.UsersDao(pool)
images_dao = dao.ImagesDao(pool)
climbs_dao = dao.ClimbsDao(pool)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(userid):
    return users_dao.get_by_id(userid)


@app.before_request
def before_request():
    g.summits_dao = summits_dao
    g.users_dao = users_dao
    g.images_dao = images_dao
    g.climbs_dao = climbs_dao

import thousands.views
import thousands.auth

import os
from flask import Flask, g, request
import psycopg2
import psycopg2.pool
import psycopg2.extensions
import dao
from flask.ext.login import LoginManager
from yoyo import read_migrations
import yoyo.exceptions
import logging

from oauth2client.client import OAuth2WebServerFlow
#logging.basicConfig()

PG_DSN="dbname=su user=rush"
VK_CLIENT_ID="4890287"
VK_API_VERSION="5.32"
SU_CLIENT_ID="thousands"

app = Flask(__name__)
app.config.from_object(__name__)
if os.environ.has_key('THOUSANDS_CONF'):
    app.config.from_envvar('THOUSANDS_CONF')
if os.environ.has_key('OPENSHIFT_DATA_DIR'):
    app.config.from_pyfile(os.path.join(os.environ['OPENSHIFT_DATA_DIR'], 'thousands.conf'))

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

vk_flow = OAuth2WebServerFlow(
        app.config['VK_CLIENT_ID'],
        client_secret = app.config['VK_CLIENT_SECRET'],
        scope = 'email',
        redirect_uri = 'http://1000.southural.ru/login/vk',
        auth_uri = 'https://oauth.vk.com/authorize',
        token_uri = 'https://oauth.vk.com/access_token',
        revoke_uri = None,
        device_uri = None,
        state = 'state'
        )
su_flow = OAuth2WebServerFlow(
        app.config['SU_CLIENT_ID'],
        client_secret = app.config['SU_CLIENT_SECRET'],
        scope = 'openid email profile',
        redirect_uri = 'http://1000.southural.ru/login/su',
        auth_uri = 'http://www.southural.ru/oauth2/authorize',
        token_uri = 'http://www.southural.ru/oauth2/token',
        revoke_uri = None,
        device_uri = None,
        state = 'state'
        )
@login_manager.user_loader
def load_user(userid):
    return users_dao.get_by_id(userid)

@app.before_request
def before_request():
    g.summits_dao = summits_dao
    g.users_dao = users_dao
    g.images_dao = images_dao
    g.climbs_dao = climbs_dao
    g.vk_flow = vk_flow
    g.su_flow = su_flow

import thousands.views
import thousands.auth

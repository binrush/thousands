from flask import Flask, g, request
import psycopg2.pool
import psycopg2.extensions
import dao
from flask.ext.login import LoginManager

PG_DSN="dbname=su user=rush"
VK_CLIENT_ID="4890287"
VK_API_VERSION="5.32"

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('THOUSANDS_CONF')

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
pool = psycopg2.pool.SimpleConnectionPool(1, 10, app.config['PG_DSN'])
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
    g.auth_links = [{ 
        'href': 
            'https://oauth.vk.com/authorize?client_id=%s&scope=email&redirect_uri=%svk_login&response_type=code&v=%s&state=state' 
                % ( app.config['VK_CLIENT_ID'], request.url_root, app.config['VK_API_VERSION']), 
        'title': 'vk.com' }]

import thousands.views

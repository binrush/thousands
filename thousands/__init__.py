from flask import Flask, g, request
import psycopg2.pool
import dao
from contextlib import contextmanager

PG_DSN="dbname=su user=rush"
VK_CLIENT_ID="4890287"
VK_API_VERSION="5.32"

app = Flask(__name__)
app.config.from_object(__name__)

pool = psycopg2.pool.SimpleConnectionPool(1, 10, app.config['PG_DSN'])
summits_dao = dao.SummitsDao(pool)

@app.before_request
def before_request():
    g.summits_dao = summits_dao
    g.auth_links = [{ 
        'href': 
            'https://oauth.vk.com/authorize?client_id=%s&scope=email&redirect_uri=%svk_login&response_type=code&v=%s&state=state' 
                % ( app.config['VK_CLIENT_ID'], request.url_root, app.config['VK_API_VERSION']), 
        'title': 'vk.com' }]

import thousands.views

# coding: utf-8
import os
from flask import Flask, g
import psycopg2
import psycopg2.pool
import psycopg2.extensions
import bleach
import dao
from flask.ext.login import LoginManager
from yoyo import read_migrations
import yoyo.exceptions
import logging
from logging.handlers import SMTPHandler


PG_DSN = "dbname=thousands user=postgres"
PG_POOL_SIZE = 20
VK_CLIENT_ID = "4890287"
VK_CLIENT_SECRET = "fake-vk-client-secret"
SU_CLIENT_ID = "thousands"
SU_CLIENT_SECRET = "fake-su-client-secret"
MAIL_SUBJECT = "thousands app failed"
LOGLEVEL = "info"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

app = Flask(__name__)
app.config.from_object(__name__)
if 'THOUSANDS_CONF' in os.environ:
    app.config.from_envvar('THOUSANDS_CONF')
if 'OPENSHIFT_DATA_DIR' in os.environ:
    app.config.from_pyfile(os.path.join(os.environ['OPENSHIFT_DATA_DIR'],
                           'thousands.conf'))

if not app.debug:
    loggers = [app.logger, logging.getLogger('yoyo')]

    if 'LOGDIR' in app.config:
        main_handler = logging.handlers.RotatingFileHandler(
            os.path.join(app.config['LOGDIR'], 'thousands.log'),
            maxBytes=1024*1024*1024,
            backupCount=10,
            encoding='utf-8')
    else:
        main_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(formatter)

    map(lambda x: x.addHandler(main_handler), loggers)
    app.logger.setLevel(getattr(logging, app.config['LOGLEVEL'].upper()))

    if 'ADMIN_MAIL' in app.config:
        mail_handler = SMTPHandler(
            app.config['SMTP_HOST'],
            app.config['SMTP_FROMADDR'],
            app.config['ADMIN_MAIL'],
            app.config['MAIL_SUBJECT'],
            (app.config['SMTP_USER'], app.config['SMTP_PASSWORD']),
            ())
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(formatter)
        map(lambda x: x.addHandler(mail_handler), loggers)

else:
    logging.getLogger('yoyo').addHandler(logging.StreamHandler())


psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
pool = psycopg2.pool.SimpleConnectionPool(1,
                                          PG_POOL_SIZE,
                                          app.config['PG_DSN'])

migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
conn = pool.getconn()
yoyo.exceptions.register(psycopg2.DatabaseError)
migrations = read_migrations(conn, psycopg2.paramstyle, migrations_dir)
migrations.to_apply().apply()
conn.commit()
pool.putconn(conn)

summits_dao = dao.SummitsDao(pool)
users_dao = dao.UsersDao(pool)
images_dao = dao.DatabaseImagesDao(pool)
climbs_dao = dao.ClimbsDao(pool)

login_manager = LoginManager()
login_manager.init_app(app)


def shorten_url(attrs, new=False):
    """Shorten overly-long URLs in the text."""
    maxlen = 50
    if not new:  # Only looking at newly-created links.
        return attrs
    # _text will be the same as the URL for new links.
    text = attrs['_text']
    if len(text) > maxlen:
        attrs['_text'] = text[0:maxlen-3] + '...'
    return attrs


@app.template_filter('linkify')
def linkify(s):
    return bleach.linkify(s, [shorten_url])


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

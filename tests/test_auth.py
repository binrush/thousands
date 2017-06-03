import mock
import pytest
from urlparse import urlparse, parse_qsl, urlunparse

from thousands import app
from thousands.model import User
from . import captured_templates


def test_login():
    templates = []
    with captured_templates(app, templates):
        r = app.test_client().get('/login')
    assert r.status_code == 200
    assert len(templates) == 1
    template, context = templates[0]
    assert template.name == '/login.html'
    assert context['next'] is None

    templates = []
    with captured_templates(app, templates):
        r = app.test_client().get('/login?next=/top')
    template, context = templates[0]
    assert context['next'] == '/top'
    assert 'href="/login/vk?next=%2Ftop"' in r.data
    assert 'href="/login/su?next=%2Ftop"' in r.data


@pytest.mark.parametrize('sn,auth_url,scope', [
    ['vk', 'https://oauth.vk.com/authorize', None],
    ['su', 'https://www.southural.ru/oauth2/authorize', 'openid profile']
])
def test_login_redirect(sn, auth_url, scope):
    r = app.test_client().get('/login/' + sn)
    assert r.status_code == 302
    redirected_to = urlparse(r.headers['Location'])
    assert urlunparse(redirected_to._replace(query=None)) == auth_url
    params = dict(parse_qsl(redirected_to.query, keep_blank_values=True))
    assert params['client_id'] == app.config[sn.upper() + '_CLIENT_ID']
    assert params.get('scope', None) == scope
    assert params['redirect_uri'] == \
           'http://localhost/login/{}/authorized'.format(sn)


@pytest.mark.parametrize('url',[
    '/login/vk/authorized',
    '/login/su/authorized'
])
def test_login_authorized_denied(url):
    with mock.patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response',
                    return_value=None):
        resp = app.test_client().get(url)
        assert resp.status_code == 302


@pytest.mark.parametrize('url',[
    '/login/vk/authorized',
    '/login/su/authorized'
])
def test_login_authorized_new_user(url):
    mock_response = {
        'user_id': 'mock_uid',
        'access_token': 'mock_access_token'
    }
    with mock.patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response',
                    return_value=mock_response),\
         mock.patch('thousands.auth.get_user',
                    return_value=(User(id=1, name='test'), False)):
        resp = app.test_client().get(url)
        assert resp.status_code == 302

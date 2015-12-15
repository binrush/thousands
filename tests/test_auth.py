import mock
import pytest
from thousands import auth

from oauth2client.client import FlowExchangeError


@pytest.fixture
def mock_request():
    req = mock.MagicMock()
    req.args = {'code': '12345'}
    return req


@pytest.fixture
def mock_request_error():
    req = mock.MagicMock()
    req.args = {'error':             'some error',
                'error_description': 'some error description'}
    return req


@pytest.fixture
def mock_flow_exception():
    flow = mock.MagicMock()
    flow.step2_exchange.side_effect = FlowExchangeError
    return flow

@pytest.fixture
def mock_get_user():
    return mock.MagicMock(return_value=(mock.MagicMock(), True))


def test_oauth_login_error(mock_request_error):
    with pytest.raises(auth.AuthError) as e:
        auth.oauth_login(mock_request_error,
                         mock.MagicMock(),
                         mock.MagicMock())
    assert e.value.message == 'some error description'


def test_oauth_login_flow_exc(mock_flow_exception, mock_request):
    with pytest.raises(auth.AuthError):
        auth.oauth_login(mock_request,
                         mock_flow_exception,
                         mock.MagicMock())
    mock_flow_exception.step2_exchange.assert_called_with('12345')


# def test_oauth_login(mock_request, mock_get_user):
#     response = auth.oauth_login(mock_request,
#                                 mock.MagicMock(),
#                                 mock_get_user)
#     print response


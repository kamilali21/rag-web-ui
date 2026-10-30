"""Privacy and adversarial API checks; no real credentials or external requests."""
import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.http_privacy import APIPrivacyMiddleware, install_http_privacy
from tests.test_phase2_authorization import world
from tests.test_phase3_authentication import otp, login, csrf


@pytest.mark.parametrize('path', ['/api/researcher/profile', '/api/researcher/requests',
    '/api/ai-settings', '/api/knowledge-base', '/api/chat/', '/api/api-keys/', '/api/insights/history'])
def test_owner_responses_and_authentication_failures_are_not_cacheable(world, path):
    w = world
    owner = w.client.get(path, headers=w.headers(w.alice))
    assert owner.status_code == 200, (path, owner.text)
    assert owner.headers['cache-control'] == 'no-store'
    assert owner.headers['x-content-type-options'] == 'nosniff'
    denied = w.client.get(path)
    assert denied.status_code == 401
    assert denied.headers['cache-control'] == 'no-store'


def test_validation_does_not_echo_password_otp_prompt_or_key(world):
    secret = 'SYNTHETIC-SECRET-NOT-REAL'
    for path, payload in [
        ('/api/auth/register', {'email': 'bad-email', 'username': 'user', 'password': {'secret': secret}}),
        ('/api/auth/verify-otp', {'email': 'alice@uaf.edu.pk', 'code': secret}),
        ('/api/retrieval/query', {'query': {'private_prompt': secret}, 'scope': 'private'}),
        ('/api/ai-settings', {'provider': 'attacker', 'model': 'x', 'api_key': secret, 'consent': True}),
    ]:
        method = 'PUT' if path == '/api/ai-settings' else 'POST'
        response = world.client.request(method, path, json=payload, headers=world.headers(world.alice))
        assert response.status_code == 422
        assert secret not in response.text and 'private_prompt' not in response.text
        assert response.headers['cache-control'] == 'no-store'


def test_unhandled_errors_are_private_and_generic():
    app = FastAPI()
    install_http_privacy(app)
    @app.get('/api/failure')
    def fail():
        raise RuntimeError('SYNTHETIC-SECRET-NOT-REAL')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/failure')
    assert response.status_code == 500
    assert response.headers['cache-control'] == 'no-store'
    assert 'SYNTHETIC-SECRET' not in response.text


def test_privacy_headers_do_not_buffer_or_rewrite_streamed_answer_frames():
    delivered = []
    async def downstream(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'text/event-stream')]})
        for index in range(2):
            await send({'type': 'http.response.body', 'body': f'frame-{index}'.encode(), 'more_body': index == 0})
            assert delivered[-1]['body'] == f'frame-{index}'.encode()
    async def send(message):
        delivered.append(message)
    asyncio.run(APIPrivacyMiddleware(downstream)({'type': 'http', 'path': '/api/chat/1/messages'}, None, send))
    assert len(delivered) == 3
    assert (b'cache-control', b'no-store') in delivered[0]['headers']


def test_stolen_csrf_or_forged_cookie_cannot_authenticate_and_logout_revokes_replay(otp):
    w = otp
    login(w)
    from app.services.auth_sessions import cookie_names
    session_name, _ = cookie_names()
    original = w.client.cookies.get(session_name)
    # A guessed bearer cookie plus the real CSRF token is not a login credential.
    with TestClient(w.app, base_url='https://testserver') as attacker:
        attacker.cookies.set(session_name, 'a' * 43)
        response = attacker.get('/api/researcher/profile', headers=csrf(w))
        assert response.status_code == 401
    assert w.client.post('/api/auth/logout', headers=csrf(w)).status_code == 200
    with TestClient(w.app, base_url='https://testserver') as attacker:
        attacker.cookies.set(session_name, original)
        assert attacker.get('/api/insights/history').status_code == 401

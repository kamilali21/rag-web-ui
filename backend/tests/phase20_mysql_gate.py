"""Initialize ONLY the guarded disposable schema and exercise MySQL security gates."""
import os
import time

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import settings


def run():
    uri = os.environ['PHASE2_TEST_DATABASE_URI']
    url = make_url(uri)
    if url.host != '127.0.0.1' or url.database != 'researchiq_phase2_test':
        raise SystemExit('Refusing a non-test database')
    settings.SQLALCHEMY_DATABASE_URI = uri
    engine = sa.create_engine(uri)
    for attempt in range(30):
        try:
            with engine.connect() as connection:
                assert connection.scalar(sa.text('SELECT DATABASE()')) == 'researchiq_phase2_test'
            break
        except sa.exc.OperationalError:
            time.sleep(2)
    else:
        raise SystemExit('Disposable MySQL was not ready')
    engine.dispose()
    command.upgrade(Config('alembic.ini'), 'head')
    return pytest.main([
        'tests/test_phase3_authentication.py::test_mysql_concurrent_requests_allow_one_winner',
        'tests/test_phase3_authentication.py::test_mysql_concurrent_new_users_do_not_gap_lock_each_other',
        'tests/test_phase20_security.py', '-q', '--tb=short',
        '--junitxml=.local/tmp/phase20-mysql.xml',
    ])


if __name__ == '__main__':
    raise SystemExit(run())

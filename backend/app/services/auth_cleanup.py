"""Added by ChatGPT: bounded housekeeping for expired authentication records only.

Run periodically with `python -m app.services.auth_cleanup`. No scheduler or
startup deletion is installed; expired records remain unusable without cleanup.
"""
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.authentication import AuthRateLimit, AuthSession, EmailOTP


def purge_expired(db, batch_size=1000):
    # Retain one day after expiry for diagnostics, without retaining raw codes/tokens.
    cutoff = datetime.utcnow() - timedelta(days=1)
    counts = {}
    for model, key in [(EmailOTP, EmailOTP.id), (AuthSession, AuthSession.id),
                       (AuthRateLimit, AuthRateLimit.key_hash)]:
        keys = [row[0] for row in db.query(key).filter(model.expires_at < cutoff)
                .order_by(model.expires_at).limit(batch_size).all()]
        # Recheck expiry under the DELETE lock so a refreshed rate-limit row survives.
        counts[model.__tablename__] = db.query(model).filter(
            key.in_(keys), model.expires_at < cutoff).delete(synchronize_session=False) if keys else 0
        db.commit()
    return counts


if __name__ == "__main__":
    with SessionLocal() as session:
        print(purge_expired(session))

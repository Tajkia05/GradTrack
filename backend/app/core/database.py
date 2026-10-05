# database.py — CONNECTS THE BACKEND TO POSTGRESQL (our shared Neon database).

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Neon gives a URL starting with "postgresql://". SQLAlchemy needs to be told which
# driver to use ("psycopg"), so we add it here. That way everyone can paste the
# Neon URL into .env exactly as Neon shows it.
_url = settings.database_url
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)

# The connection to the database.
# pool_pre_ping: Neon puts the database to sleep when nobody uses it, which closes
# old connections. This checks a connection still works before using it.
engine = create_engine(_url, pool_pre_ping=True)

# A "session" is one conversation with the database (read some rows, save some rows).
# SessionLocal() creates a new session.
SessionLocal = sessionmaker(bind=engine, autoflush=False)


# Every database table class (in the models.py files) inherits from Base.
# Example:  class User(Base): ...
class Base(DeclarativeBase):
    pass


def get_db():
    """Give each API request its own database session, and close it when done.

    Use it in an endpoint like this:
        def my_endpoint(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

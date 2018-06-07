# coding: utf-8


import sqlalchemy as sa
import threading
from sqlalchemy import orm
from sqlalchemy.ext import declarative

from backend import config

Base = declarative.declarative_base()


class Session:
    _session_class = None

    def __init__(self, init_schema=False):
        session_class = self._get_session_class()
        self._session = session_class()

        if init_schema:
            Base.metadata.create_all(self._session.get_bind())

    def _get_session_class(self):
        if not Session._session_class:
            with threading.Lock():
                if not Session._session_class:
                    Session._session_class = orm.sessionmaker(
                        bind=self._create_engine()
                    )

        return Session._session_class

    def _create_engine(self):
        return sa.create_engine(config.Config.get().db_url)

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        else:
            self._session.commit()
        self._session.close()


class Database(Base):
    __tablename__ = 'databases'

    __table_args__ = (
        sa.UniqueConstraint('schema_version'),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    schema_version = sa.Column(sa.Integer, nullable=False)
    version = sa.Column(sa.String, nullable=False)
    content = orm.deferred(sa.Column(sa.Binary, nullable=False))

    def __init__(self, schema_version=None, version=None, content=None):
        self.schema_version = schema_version
        self.version = version
        self.content = content

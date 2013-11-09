# coding: utf-8


from __future__ import absolute_import, unicode_literals

from sqlalchemy import create_engine, Integer, Column, String, Binary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, deferred

from backend.util import Config


engine = create_engine(Config.get_config_value(Config.VALUE_DB_URL))
db_session = scoped_session(sessionmaker(bind=engine))


Base = declarative_base()
Base.query = db_session.query_property()


class Database(Base):
    __tablename__ = 'databases'

    id = Column(Integer, primary_key=True)
    schema_version = Column(Integer, unique=True, nullable=False)
    version = Column(String, unique=True, nullable=False)
    contents = deferred(Column(Binary, nullable=False))

    def __init__(self, schema_version=None, version=None, contents=None):
        self.schema_version = schema_version
        self.version = version
        self.contents = contents

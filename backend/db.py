# coding: utf-8


from __future__ import absolute_import, unicode_literals

from sqlalchemy import create_engine, Integer, Column, String, Binary, \
    UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, deferred

from backend.util import Config


engine = create_engine(Config.get_config_value(Config.VALUE_DB_URL))
db_session = scoped_session(sessionmaker(bind=engine))


Base = declarative_base()
Base.query = db_session.query_property()


class Database(Base):
    __tablename__ = 'databases'

    __table_args__ = (
        UniqueConstraint('schema_version', 'version'),
    )

    id = Column(Integer, primary_key=True)
    schema_version = Column(Integer, nullable=False)
    version = Column(String, nullable=False)
    contents = deferred(Column(Binary, nullable=False))

    def __init__(self, schema_version=None, version=None, contents=None):
        self.schema_version = schema_version
        self.version = version
        self.contents = contents

    @classmethod
    def find_by_schema_version(cls, schema_version):
        return (Database.query
                .filter(Database.schema_version == schema_version)
                .first())

    @classmethod
    def find_latest(cls):
        return (Database.query
                .order_by(Database.schema_version.desc())
                .first())

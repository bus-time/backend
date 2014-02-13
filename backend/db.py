# coding: utf-8


import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm

from backend import util


engine = sa.create_engine(
    util.Config.get_config_value(util.Config.VALUE_DB_URL)
)
database_session = orm.scoped_session(orm.sessionmaker(bind=engine))

Base = declarative.declarative_base()
Base.query = database_session.query_property()


class Database(Base):
    __tablename__ = 'databases'

    __table_args__ = (
        sa.UniqueConstraint('schema_version', 'version'),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    schema_version = sa.Column(sa.Integer, nullable=False)
    version = sa.Column(sa.String, nullable=False)
    contents = orm.deferred(sa.Column(sa.Binary, nullable=False))

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

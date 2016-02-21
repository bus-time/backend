# coding: utf-8


import tempfile

import pytest

from backend import db, util, service


class SqliteDbConfig(util.Config):
    SQLITE_DB_URL = 'sqlite:///{0}'

    def __init__(self):
        self._db_url = self.SQLITE_DB_URL.format(self._get_temp_file_name())

    def _get_temp_file_name(self):
        with tempfile.NamedTemporaryFile() as f:
            return f.name

    @property
    def db_url(self):
        return self._db_url

    @property
    def deployment_key_dir(self):
        return None


class BaseDbAwareTest:
    MIN_VERSION = 1
    MAX_VERSION = 5

    def init_database(self):
        util.Config.init(SqliteDbConfig())

        with db.Session(init_schema=True) as session:
            for x in range(self.MIN_VERSION, self.MAX_VERSION + 1):
                session.add(
                    db.Database(
                        schema_version=x,
                        version=str(x),
                        contents=bytes(x))
                )


class TestDatabaseQuery(BaseDbAwareTest):
    def test_get_existing_version_info_succeeds(self):
        self.init_database()

        schema_version, version = service.DatabaseQuery().get_version_info(
            self.MIN_VERSION
        )

        assert schema_version == self.MIN_VERSION
        assert version == str(self.MIN_VERSION)

    def test_get_non_existing_version_info_fails(self):
        self.init_database()

        with pytest.raises(service.NoDatabaseFound):
            service.DatabaseQuery().get_version_info(
                self.MAX_VERSION + 1
            )

    def test_get_existing_contents_succeeds(self):
        self.init_database()
        contents = service.DatabaseQuery().get_contents(self.MIN_VERSION)
        assert contents == bytes(self.MIN_VERSION)

    def test_get_non_existing_contents_fails(self):
        self.init_database()

        with pytest.raises(service.NoDatabaseFound):
            service.DatabaseQuery().get_contents(self.MAX_VERSION + 1)

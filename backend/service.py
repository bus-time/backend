# coding: utf-8


from backend import db


class DatabaseQuery:
    def get_version_info(self, schema_version):
        with db.Session() as session:
            database = self._find_database(session, schema_version)
            if not database:
                raise NoDatabaseFound()
            return database.schema_version, database.version

    def _find_database(self, session, schema_version):
        return (session.query(db.Database)
                .filter(db.Database.schema_version == schema_version)
                .first())

    def get_contents(self, schema_version):
        with db.Session() as session:
            database = self._find_database(session, schema_version)
            if not database:
                raise NoDatabaseFound()

            return database.contents


class NoDatabaseFound(RuntimeError):
    pass

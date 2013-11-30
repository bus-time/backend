# coding: utf-8


from __future__ import absolute_import, unicode_literals
import httplib

from flask import jsonify, url_for, make_response, request
from werkzeug.exceptions import abort

from backend.server import app
from backend.db import Database, db_session


CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=file.db.gz'

FORM_STRING_DATA_ENCODING = 'utf8'
FORM_CONTENTS_KEY = 'contents'
FORM_VERSION_KEY = 'version'
FORM_SCHEMA_VERSION_KEY = 'schema-version'

SCHEMA_VERSION_MIN = 1
SCHEMA_VERSION_MAX = 2 ** 16

ERROR_MORE_RECENT_SCHEMA_DEPLOYED = 'More recent schema deployed'
ERROR_VERSION_ALREADY_DEPLOYED = 'Version is already deployed'
ERROR_INVALID_SCHEMA_VERSION = 'Invalid schema version specified'


@app.route('/')
def index():
    return 'Hello from Bus Time Backend!'


@app.route('/db-updates/version/<int:schema_version>')
def db_updates_version(schema_version):
    database = (Database.query
                .filter(Database.schema_version == schema_version)
                .first())

    if not database:
        abort(httplib.NOT_FOUND)

    return jsonify(build_version_info_dict(database))


def build_version_info_dict(database):
    return {
        'schema_version': database.schema_version,
        'version': database.version,
        'file_url': full_url_for('db_updates_file', key=database.id)
    }


def full_url_for(endpoint, **values):
    return url_for(endpoint, _external=True, **values)


@app.route('/db-updates/file/<int:key>')
def db_updates_file(key):
    database = (Database.query
                .filter(Database.id == key)
                .first())

    if not database:
        abort(httplib.NOT_FOUND)

    return build_db_contents_response(database.contents)


def build_db_contents_response(contents):
    response = make_response(contents)
    response.headers['Content-Type'] = CONTENT_TYPE_OCTET_STREAM
    response.headers['Content-Disposition'] = CONTENT_DISPOSITION_DB_FILE
    return response


@app.route('/db-updates/deploy', methods=['POST'])
def db_updates_deploy():
    try:
        contents, schema_version, version = read_deploy_data(request)
        update_database(contents, schema_version, version)
    except InvalidSchemaVersionError:
        return make_error_response(ERROR_INVALID_SCHEMA_VERSION,
                                   httplib.BAD_REQUEST)
    except DeployConfictError as e:
        return make_error_response(e.error, httplib.CONFLICT)

    return db_updates_version(schema_version)


def read_deploy_data(request):
    contents = request.files[FORM_CONTENTS_KEY].stream.read()
    schema_version = read_schema_version(request)
    version = read_form_string_data(request, FORM_VERSION_KEY)

    return contents, schema_version, version


def read_schema_version(request):
    try:
        schema_version_str = read_form_string_data(
            request, FORM_SCHEMA_VERSION_KEY)
        schema_version_int = int(schema_version_str)
    except ValueError:
        raise InvalidSchemaVersionError()

    if not (SCHEMA_VERSION_MIN <= schema_version_int <= SCHEMA_VERSION_MAX):
        raise InvalidSchemaVersionError()

    return schema_version_int


def read_form_string_data(request, key):
    binary = request.files[key].stream.read()
    return binary.decode(FORM_STRING_DATA_ENCODING)


def update_database(contents, schema_version, version):
    database = get_latest_deployed_database()

    check_database_conflicts(database, schema_version, version)

    if database and database.schema_version == schema_version:
        delete_database(database)
    create_database(contents, schema_version, version)

    db_session.commit()


def check_database_conflicts(database, schema_version, version):
    if database and database.schema_version > schema_version:
        raise DeployConfictError(ERROR_MORE_RECENT_SCHEMA_DEPLOYED)
    if database and database.version == version:
        raise DeployConfictError(ERROR_VERSION_ALREADY_DEPLOYED)


def delete_database(database):
    db_session.delete(database)
    db_session.flush()


def create_database(contents, schema_version, version):
    database = Database(schema_version=schema_version,
                        version=version,
                        contents=contents)
    db_session.add(database)


def make_error_response(error, code):
    response = {
        'error': error
    }

    return jsonify(response), code


def get_latest_deployed_database():
    return (Database.query
            .order_by(Database.schema_version.desc())
            .first())


class InvalidSchemaVersionError(ValueError):
    pass


class DeployConfictError(ValueError):
    def __init__(self, error):
        self.error = error

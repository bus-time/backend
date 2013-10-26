# coding: utf-8


from __future__ import absolute_import, unicode_literals
import httplib

from flask import jsonify, url_for, make_response
from werkzeug.exceptions import abort

from backend.app import app
from backend.db import Database


CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=file.db.gz'


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

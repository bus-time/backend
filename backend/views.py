# coding: utf-8


import http.client as http

import flask
from werkzeug import exceptions as wzex

from backend import service
from backend.server import app


HEADER_X_CONTENT_SIGNATURE = 'X-Content-Signature'
MAX_UPDATE_CONTENT_LENGTH = 5 * 1024 * 1024


@app.route('/databases/<int:schema_version>')
def database_info(schema_version):
    try:
        version = service.DatabaseQuery().get_version(schema_version)
        return flask.jsonify(
            dict(schema_version=schema_version, version=version)
        )
    except service.NoDatabaseFound:
        wzex.abort(http.NOT_FOUND)


@app.route('/databases/<int:schema_version>/contents')
def database_contents(schema_version):
    try:
        contents = service.DatabaseQuery().get_content(schema_version)
        return HttpUtils.build_database_contents_response(contents)
    except service.NoDatabaseFound:
        wzex.abort(http.NOT_FOUND)


@app.route('/databases', methods=['POST'])
def database_deploy():
    if flask.request.content_length > MAX_UPDATE_CONTENT_LENGTH:
        wzex.abort(http.BAD_REQUEST)
        return

    signature_text = flask.request.headers[HEADER_X_CONTENT_SIGNATURE]
    json_data = flask.request.get_data(as_text=True)

    try:
        update = service.DatabaseUpdate()
        update_content = update.get_update_content(json_data, signature_text)
        update.apply_update(update_content)
    except service.InvalidSignatureError:
        wzex.abort(http.UNAUTHORIZED)
    except service.InvalidUpdateContentError:
        wzex.abort(http.BAD_REQUEST)

    return flask.jsonify(status='success')


class HttpUtils(object):
    HEADER_CONTENT_TYPE = 'Content-Type'
    HEADER_CONTENT_DISPOSITION = 'Content-Disposition'
    HEADER_X_CONTENT_SHA256 = 'X-Content-SHA256'

    CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
    CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=bus-time.db'

    @classmethod
    def build_database_contents_response(cls, contents):
        response = flask.make_response(contents)

        headers = cls._build_extra_contents_headers(contents)
        for name, value in headers.items():
            response.headers[name] = value

        return response

    @classmethod
    def _build_extra_contents_headers(cls, contents):
        return {
            cls.HEADER_CONTENT_TYPE: cls.CONTENT_TYPE_OCTET_STREAM,
            cls.HEADER_CONTENT_DISPOSITION: cls.CONTENT_DISPOSITION_DB_FILE,
            cls.HEADER_X_CONTENT_SHA256: service.Sha256().make_hash(contents)
        }

    @classmethod
    def make_error_response(cls, error, code):
        response = {
            'error': error
        }

        return flask.jsonify(response), code

# coding: utf-8


from http import HTTPStatus

import flask
from flask.ext.classy import FlaskView, route

from backend import service
from backend.server import app


class DatabasesView(FlaskView):
    HEADER_CONTENT_TYPE = 'Content-Type'
    HEADER_CONTENT_DISPOSITION = 'Content-Disposition'
    HEADER_X_CONTENT_SHA256 = 'X-Content-SHA256'
    HEADER_X_CONTENT_SIGNATURE = 'X-Content-Signature'

    CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
    CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=bus-time.db'

    MAX_UPDATE_CONTENT_LENGTH = 5 * 1024 * 1024

    @route('/<int:schema_version>/')
    def info(self, schema_version):
        try:
            version = service.DatabaseQuery().get_version(schema_version)
            return flask.jsonify(
                dict(schema_version=schema_version, version=version)
            )
        except service.NoDatabaseFound:
            flask.abort(HTTPStatus.NOT_FOUND)

    @route('/<int:schema_version>/content/')
    def content(self, schema_version):
        try:
            content = service.DatabaseQuery().get_content(schema_version)
            return self._build_database_contents_response(content)
        except service.NoDatabaseFound:
            flask.abort(HTTPStatus.NOT_FOUND)

    @route('/<int:schema_version>/contents/')
    def contents(self, schema_version):
        return flask.redirect(
            flask.url_for(
                'DatabasesView:content', schema_version=schema_version
            ),
            code=HTTPStatus.MOVED_PERMANENTLY
        )

    @classmethod
    def _build_database_contents_response(cls, content):
        response = flask.make_response(content)

        headers = cls._build_extra_content_headers(content)
        for name, value in headers.items():
            response.headers[name] = value

        return response

    @classmethod
    def _build_extra_content_headers(cls, contents):
        return {
            cls.HEADER_CONTENT_TYPE: cls.CONTENT_TYPE_OCTET_STREAM,
            cls.HEADER_CONTENT_DISPOSITION: cls.CONTENT_DISPOSITION_DB_FILE,
            cls.HEADER_X_CONTENT_SHA256: service.Sha256().make_hash(contents)
        }

    @route('/', methods=['POST'])
    def deploy(self):
        if flask.request.content_length > self.MAX_UPDATE_CONTENT_LENGTH:
            flask.abort(HTTPStatus.BAD_REQUEST)
            return

        signature_text = flask.request.headers[self.HEADER_X_CONTENT_SIGNATURE]
        json_data = flask.request.get_data(as_text=True)

        try:
            update = service.DatabaseUpdate()
            update_content = update.get_update_content(json_data, signature_text)
            update.apply_update(update_content)
        except service.InvalidSignatureError:
            flask.abort(HTTPStatus.UNAUTHORIZED)
        except service.InvalidUpdateContentError:
            flask.abort(HTTPStatus.BAD_REQUEST)

        return flask.jsonify(status='success')


DatabasesView.register(app)

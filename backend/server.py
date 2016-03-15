# coding: utf-8

from http import HTTPStatus

import flask
from flask.ext import compress
from werkzeug.exceptions import default_exceptions, HTTPException

from backend import util


def create_flask_app():
    flask_app = flask.Flask(__name__)

    flask_app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
    flask_app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                              'application/octet-stream']

    _apply_json_error_handlers(flask_app)

    return flask_app


def _apply_json_error_handlers(flask_app):
    for code in default_exceptions.keys():
        flask_app.error_handler_spec[None][code] = _make_json_error


def _make_json_error(ex):
    if isinstance(ex, HTTPException):
        status_code = ex.code
        message = str(ex)
    else:
        status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        message = '{}: Internal server error'.format(status_code)

    response = flask.jsonify(message=message)
    response.status_code = status_code

    return response


app = create_flask_app()
compressor = compress.Compress(app)

util.Config.init()

import backend.views

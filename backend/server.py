# coding: utf-8

from http import HTTPStatus

import flask
from flask.ext import compress

from backend import util, web_util


def create_flask_app():
    flask_app = flask.Flask(__name__)

    flask_app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
    flask_app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                              'application/octet-stream']

    web_util.JsonHttpExceptionHandler().init(flask_app)

    return flask_app


app = create_flask_app()
compressor = compress.Compress(app)

util.Config.init()

import backend.views

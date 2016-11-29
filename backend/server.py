# coding: utf-8


import flask
import flask_compress as compress

from backend import config, web_util


def create_flask_app():
    flask_app = flask.Flask(__name__)

    flask_app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
    flask_app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                              'application/octet-stream']

    web_util.JsonHttpExceptionHandler().init(flask_app)

    return flask_app


app = create_flask_app()
compressor = compress.Compress(app)

config.Config.init()

import backend.views

# coding: utf-8


from __future__ import absolute_import

import flask
from flask.ext import compress


app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

compressor = compress.Compress(app)
app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                    'application/octet-stream']

import backend.views


@app.teardown_appcontext
def shutdown_session(exception=None):
    from backend import db
    db.database_session.remove()

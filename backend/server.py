# coding: utf-8


from __future__ import absolute_import

from flask import Flask
from flask.ext.compress import Compress


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

compressor = Compress(app)
app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                    'application/octet-stream']

import backend.views


@app.teardown_appcontext
def shutdown_session(exception=None):
    from backend.db import db_session
    db_session.remove()

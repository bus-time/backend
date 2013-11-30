# coding: utf-8


from __future__ import absolute_import

from flask import Flask


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

import backend.views


@app.teardown_appcontext
def shutdown_session(exception=None):
    from backend.db import db_session
    db_session.remove()

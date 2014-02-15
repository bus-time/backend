# coding: utf-8


import flask
from flask.ext import compress
from werkzeug import exceptions as wzex


app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

compressor = compress.Compress(app)
app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                    'application/octet-stream']


import backend.views


for code in wzex.default_exceptions.keys():
    app.error_handler_spec[None][code] = backend.views.handle_error


@app.teardown_appcontext
def shutdown_session(exception=None):
    from backend import db
    db.database_session.remove()

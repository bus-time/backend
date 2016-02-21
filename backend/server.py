# coding: utf-8


import flask
from flask.ext import compress

from backend import util


app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

compressor = compress.Compress(app)
app.config['COMPRESS_MIMETYPES'] = ['application/json',
                                    'application/octet-stream']

util.Config.init()


import backend.views

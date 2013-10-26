# coding: utf-8


from __future__ import absolute_import, unicode_literals

from backend.app import app


@app.route('/')
def index():
    return 'Hello from Bus Time Backend!'

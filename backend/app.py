# coding: utf-8


from __future__ import absolute_import

from flask import Flask


app = Flask(__name__)
import backend.views

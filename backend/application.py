# coding: utf-8


from __future__ import absolute_import, unicode_literals
from argparse import ArgumentParser

from backend.server import app


def main():
    run_server(parse_args())


def parse_args():
    parser = ArgumentParser()

    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--use-reloader', action='store_true')

    return parser.parse_args()


def run_server(args):
    app.run(debug=args.debug, use_reloader=args.use_reloader)

# coding: utf-8


from __future__ import absolute_import, unicode_literals
from argparse import ArgumentParser

from backend import deploy
from backend.server import app


ERROR_BOTH_RUN_SERVER_AND_DEPLOY_VERSION = (
    "Arguments '--run-server' and '--deploy-version' can not be specified both")


def main():
    args = parse_args()
    error = validate_args(args)

    if error:
        print(error)
    elif args.run_server:
        run_server(args)
    elif args.deploy_version:
        deploy_version(args)
    else:
        raise RuntimeError('Invalid arguments specified')


def parse_args():
    parser = ArgumentParser()

    parser.add_argument('--run-server', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--use-reloader', action='store_true')
    parser.add_argument('--deploy-version', action='store_true')

    return parser.parse_args()


def validate_args(args):
    if args.run_server and args.deploy_version:
        return ERROR_BOTH_RUN_SERVER_AND_DEPLOY_VERSION


def run_server(args):
    app.run(debug=args.debug, use_reloader=args.use_reloader)


def deploy_version(args):
    deploy.deploy_version()

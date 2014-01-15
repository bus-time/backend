#!/usr/bin/python2
# coding: utf-8


from __future__ import absolute_import, unicode_literals
from argparse import ArgumentParser
import subprocess


def main():
    args = parse_args()
    Deployer(args.force).deploy()


def parse_args():
    parser = ArgumentParser()

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='use “git push --force” instead of just ”git push”'
    )

    return parser.parse_args()


class Deployer(object):
    def __init__(self, force):
        self.force = force

    def deploy(self):
        self.stop_web()
        self.deploy_application()
        self.start_web()

    def stop_web(self):
        subprocess.check_call(['heroku', 'maintenance:on'])
        if self.have_running_dynos():
            subprocess.check_call(['heroku', 'ps:scale', 'web=0'])

    def have_running_dynos(self):
        return subprocess.check_output(['heroku', 'ps']) != ''

    def start_web(self):
        subprocess.check_call(['heroku', 'ps:scale', 'web=0'])
        subprocess.check_call(['heroku', 'maintenance:off'])

    def deploy_application(self):
        command = ['git', 'push', 'heroku', 'HEAD:master']
        if self.force:
            command.append('--force')

        subprocess.check_call(command)

        subprocess.check_call(
            ['heroku', 'run',
             'alembic --config config/alembic.ini upgrade head']
        )


if __name__ == '__main__':
    main()

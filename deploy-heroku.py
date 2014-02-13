#!/usr/bin/python3
# coding: utf-8


import argparse
import subprocess


def main():
    args = parse_args()
    Deployer(args.force, args.remote).deploy()


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='use “git push --force” instead of just ”git push”'
    )
    parser.add_argument(
        '-r', '--remote',
        action='store',
        default='heroku',
        help='name of Heroku remote to use as the deploy target'
    )

    return parser.parse_args()


class Deployer(object):
    def __init__(self, force, remote):
        self.force = force
        self.remote = remote

    def deploy(self):
        self.stop_web()
        self.deploy_application()
        self.start_web()

    def stop_web(self):
        self.heroku_check_call(['maintenance:on'])
        if self.have_running_dynos():
            self.heroku_check_call(['ps:scale', 'web=0'])

    def heroku_check_call(self, args):
        return subprocess.check_call(self.build_heroku_command(args))

    def build_heroku_command(self, args):
        return ['heroku'] + args + ['--remote', self.remote]

    def have_running_dynos(self):
        return self.heroku_check_output(['ps']) != ''

    def heroku_check_output(self, args):
        return subprocess.check_output(self.build_heroku_command(args))

    def deploy_application(self):
        subprocess.check_call(self.build_push_command())
        self.heroku_check_call(
            ['run', 'alembic --config config/alembic.ini upgrade head']
        )

    def build_push_command(self):
        command = ['git', 'push', self.remote, 'HEAD:master']

        if self.force:
            command.append('--force')

        return command

    def start_web(self):
        self.heroku_check_call(['ps:scale', 'web=1'])
        self.heroku_check_call(['maintenance:off'])


if __name__ == '__main__':
    main()

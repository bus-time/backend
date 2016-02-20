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
        default='openshift',
        help='name of OpenShift remote to use as the deploy target'
    )

    return parser.parse_args()


class Deployer(object):
    def __init__(self, force, remote):
        self.force = force
        self.remote = remote

    def deploy(self):
        subprocess.check_call(self.build_push_command())

    def build_push_command(self):
        command = ['git', 'push', self.remote, 'HEAD:master']

        if self.force:
            command.append('--force')

        return command


if __name__ == '__main__':
    main()

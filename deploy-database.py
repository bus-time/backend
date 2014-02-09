#!/usr/bin/python2
# coding: utf-8


from __future__ import absolute_import, unicode_literals, print_function
import argparse
import getpass
import zipfile
import ConfigParser
import os
import subprocess
import tempfile
import collections
import io
import shutil

from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
import github3
import requests


class Config(object):
    ConfigKey = collections.namedtuple('ConfigKey', ['section', 'option'])

    DEFAULT_CONFIG_FILE_NAME = 'deploy-database.ini'
    CONFIG_FILE_DIR = 'config'
    CONFIG_SECTION_NAME = 'general'

    VALUE_REPO_OWNER = ConfigKey('repo', 'owner')
    VALUE_REPO_NAME = ConfigKey('repo', 'name')
    VALUE_REPO_BRANCH = ConfigKey('repo', 'branch')

    VALUE_BUILD_MAKE_TARGET = ConfigKey('build', 'make-target')
    VALUE_BUILD_MADE_FILE_NAME = ConfigKey('build', 'made-file-name')

    VALUE_DEPLOY_URL = ConfigKey('deploy', 'url')
    VALUE_DEPLOY_SIGNATURE_KEY_FILE = ConfigKey('deploy', 'signature-key-file')

    config_file_name = DEFAULT_CONFIG_FILE_NAME

    @classmethod
    def get_config_value(cls, config_key):
        parser = cls.get_config_parser()

        if not parser.has_section(config_key.section):
            parser.add_section(config_key.section)

        return parser.get(config_key.section, config_key.option)

    @classmethod
    def get_config_parser(cls):
        parser = ConfigParser.SafeConfigParser()
        parser.read(cls.get_config_file_path())
        return parser

    @classmethod
    def get_config_file_path(cls):
        return os.path.join(cls.get_config_dir_path(), cls.config_file_name)

    @classmethod
    def get_config_dir_path(cls):
        relative_path = os.path.join(cls.get_script_dir(), cls.CONFIG_FILE_DIR)
        return os.path.abspath(relative_path)

    @classmethod
    def get_script_dir(cls):
        return os.path.dirname(os.path.realpath(__file__))


class DescribeDecorator(object):
    def __init__(self, start=None, done=None):
        self.start = start
        self.done = done

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            print(self.start or '', end=' ')

            try:
                result = func(*args, **kwargs)
                print(self.done or '')
                return result
            except:
                print('')
                raise

        return wrapper


describe = DescribeDecorator


class DbDeploymentError(Exception):
    def __init__(self, reason):
        self.reason = reason


class VersionDeployer(object):
    FORM_STRING_DATA_ENCODING = 'utf8'
    FORM_CONTENTS_KEY = 'contents'
    FORM_VERSION_KEY = 'version'
    FORM_SCHEMA_VERSION_KEY = 'schema-version'
    FORM_IS_MIGRATION_UPDATE_KEY = 'is-migration-update'
    FORM_VALUE_TRUE = 'true'
    FORM_VALUE_FALSE = 'false'
    FORM_SIGNATURE_SUFFIX = '-signature'

    def __init__(self, key_file):
        self.signature_key = self.import_private_key(key_file)

    def import_private_key(self, key_file):
        return RSA.importKey(open(key_file, 'rb').read())

    def deploy_version(self):
        with DbFileMaker() as maker:
            latest_version, migrated_versions = maker.make_db_file_infos()
            self.deploy_database(latest_version, False)
            for migrated_version in migrated_versions:
                self.deploy_database(migrated_version, True)

    def deploy_database(self, file_info, is_migration_update):
        deploy_url = Config.get_config_value(Config.VALUE_DEPLOY_URL)
        files = self.build_files_dict(file_info.schema_version,
                                      file_info.version,
                                      self.read_file(file_info.file_path),
                                      is_migration_update)

        self.describe_database_deployment(file_info)
        response = requests.post(deploy_url, files=files)

        if not response.ok:
            raise DbDeploymentError(self.build_error_text(response))

    def read_file(self, file_path):
        with open(file_path, 'rb') as f:
            return f.read()

    def describe_database_deployment(self, file_info):
        message = 'Deploying database file of schema version “{0}”'
        print(message.format(file_info.schema_version))

    def build_files_dict(self, schema_version, commit_sha, contents,
                         is_migration_update):
        files = {
            self.FORM_CONTENTS_KEY: contents,
            self.FORM_SCHEMA_VERSION_KEY: unicode(schema_version).encode(
                self.FORM_STRING_DATA_ENCODING),
            self.FORM_VERSION_KEY: commit_sha.encode(
                self.FORM_STRING_DATA_ENCODING),
            self.FORM_IS_MIGRATION_UPDATE_KEY: self.bool_to_form_value(
                is_migration_update)
        }

        signed_files = dict()

        for dict_key, data in files.items():
            self.append_file_to_dict(signed_files, dict_key, data)

        return signed_files

    def bool_to_form_value(self, value):
        if value:
            return self.FORM_VALUE_TRUE
        else:
            return self.FORM_VALUE_FALSE

    def append_file_to_dict(self, dict, dict_key, data):
        dict_signature_key = '{}{}'.format(dict_key, self.FORM_SIGNATURE_SUFFIX)

        dict[dict_key] = data
        dict[dict_signature_key] = self.make_signature(data, self.signature_key)

    def make_signature(self, data, key):
        sha = SHA512.new()
        sha.update(data)

        return PKCS1_PSS.new(key).sign(sha)

    def build_error_text(self, response):
        return 'Error {} {}\n{}'.format(response.status_code,
                                        response.reason,
                                        response.text)


DbFileInfo = collections.namedtuple('DbFileInfo',
                                    ['schema_version', 'version', 'file_path'])


class DbFileMaker(object):
    ARCHIVE_FILE_NAME = 'archive.zip'
    ARCHIVE_FORMAT = 'zipball'
    EXTRACTED_ARCHIVE_DIR = 'archive'
    MIGRATION_DIR = 'migrations'
    BRANCH_HEAD_REF_FORMAT = 'heads/{}'
    VERSION_FILE_FORMAT = '{}.db'
    MIGRATION_SCRIPT_FORMAT = '{0:02d}-to-{1:02d}.sql'
    SCHEMA_DIR = 'schema'
    SCHEMA_VERSION_FILE_NAME = 'version.txt'
    ENCODING = 'utf8'

    MIN_SCHEMA_VERSION = 1
    MAX_SCHEMA_VERSION = 2 ** 31 - 1

    def __init__(self):
        self.download_dir = None

    def __enter__(self):
        self.download_dir = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        subprocess.check_call(['rm', '-rf', self.download_dir])

    def make_db_file_infos(self):
        repo = self.connect_to_repo()
        head_sha = self.get_head_sha(repo)

        self.download_repo(repo, head_sha)

        latest_version_info = self.build_latest_schema_file(head_sha)
        migrated_version_infos = self.build_migrated_schema_files(
            head_sha, latest_version_info.schema_version
        )

        return latest_version_info, migrated_version_infos

    def connect_to_repo(self):
        username, password = self.get_credentials()
        return self.login_to_repo(username, password)

    def get_credentials(self):
        return raw_input('Username: '), getpass.getpass('Password: ')

    @describe(start='Logging in to repo...', done='done.')
    def login_to_repo(self, username, password):
        repo_owner = Config.get_config_value(Config.VALUE_REPO_OWNER)
        repo_name = Config.get_config_value(Config.VALUE_REPO_NAME)

        return github3.login(username, password).repository(repo_owner,
                                                            repo_name)

    @describe(start='Obtaining HEAD SHA...', done='done.')
    def get_head_sha(self, repo):
        branch_name = Config.get_config_value(Config.VALUE_REPO_BRANCH)
        head = repo.ref(self.BRANCH_HEAD_REF_FORMAT.format(branch_name))

        if not head:
            raise DbDeploymentError(self.make_no_head_message(branch_name))

        self.describe_head_sha(head.object.sha, branch_name)

        return head.object.sha

    def make_no_head_message(self, branch_name):
        message = ('No “{}” HEAD found. It seems the repo has no commits. ' +
                   'Nothing to do.')
        return message.format(branch_name)

    def describe_head_sha(self, head_sha, branch_name):
        print("Branch “{}” HEAD is “{}”.".format(branch_name, head_sha))

    @describe(start='Downloading repo archive...', done='done.')
    def download_repo(self, repo, commit):
        archive_file = self.get_archive_file_path(self.download_dir)

        if not repo.archive(self.ARCHIVE_FORMAT, path=archive_file, ref=commit):
            raise RuntimeError('Error downloading the archive')

        zipfile.ZipFile(archive_file).extractall(self.get_extracted_dir())

    def get_archive_file_path(self, download_dir):
        return os.path.join(download_dir, self.ARCHIVE_FILE_NAME)

    def get_extracted_dir(self):
        return os.path.join(self.download_dir, self.EXTRACTED_ARCHIVE_DIR)

    def build_latest_schema_file(self, head_sha):
        latest_schema_version = self.read_schema_version()
        database_file = self.make_database_file()

        latest_schema_file = self.get_version_file_path(latest_schema_version)
        shutil.move(database_file, latest_schema_file)

        return DbFileInfo(schema_version=latest_schema_version,
                          version=head_sha,
                          file_path=latest_schema_file)

    def read_schema_version(self):
        schema_version_string = self.read_schema_version_string()

        try:
            schema_version = self.get_schema_version(schema_version_string)
        except ValueError:
            message = ('File “schema-version.txt” contains invalid version ' +
                       'string: “{}”.')
            raise ValueError(message.format(schema_version_string))

        return schema_version

    def read_schema_version_string(self):
        file_path = os.path.join(self.get_repo_dir(),
                                 self.SCHEMA_DIR,
                                 self.SCHEMA_VERSION_FILE_NAME)
        with io.open(file_path, 'r', encoding=self.ENCODING) as f:
            return '\n'.join(f.readlines()).strip()

    def get_schema_version(self, schema_version_string):
        schema_version = int(schema_version_string)
        if not self.is_valid_schema_version(schema_version):
            raise ValueError()

        return schema_version

    def is_valid_schema_version(self, schema_version):
        return (self.MIN_SCHEMA_VERSION <= schema_version <=
                self.MAX_SCHEMA_VERSION)

    def make_database_file(self):
        make_target = Config.get_config_value(Config.VALUE_BUILD_MAKE_TARGET)
        db_file_name = Config.get_config_value(
            Config.VALUE_BUILD_MADE_FILE_NAME)

        subprocess.check_call(['make', make_target,
                               '--directory', self.get_repo_dir()])
        return os.path.join(self.get_repo_dir(), db_file_name)

    def get_repo_dir(self):
        extracted_dir = self.get_extracted_dir()
        return os.path.join(extracted_dir, os.listdir(extracted_dir)[0])

    def get_version_file_path(self, schema_version):
        return os.path.join(
            self.get_migration_dir(),
            self.VERSION_FILE_FORMAT.format(schema_version)
        )

    def get_migration_dir(self):
        return os.path.join(self.get_repo_dir(), self.MIGRATION_DIR)

    def build_migrated_schema_files(self, head_sha, latest_schema_version):
        migrated_file_infos = []

        schema_version = latest_schema_version - 1
        while self.can_migrate_database(schema_version):
            self.migrate_database(schema_version)

            migrated_file_infos.append(
                DbFileInfo(
                    schema_version=schema_version,
                    version=head_sha,
                    file_path=self.get_version_file_path(schema_version)
                )
            )

            schema_version -= 1

        return migrated_file_infos

    def can_migrate_database(self, target_version):
        if target_version < self.MIN_SCHEMA_VERSION:
            return False

        if not os.path.exists(self.get_migration_script_path(target_version)):
            return False

        return True

    def get_migration_script_path(self, target_version):
        migration_script_name = self.MIGRATION_SCRIPT_FORMAT.format(
            target_version + 1, target_version
        )
        return os.path.join(self.get_migration_dir(),
                            migration_script_name)

    def migrate_database(self, target_version):
        self.describe_database_migration(target_version)

        original_dir = os.getcwd()
        os.chdir(self.get_migration_dir())

        try:
            self.run_migration_script(target_version)
        finally:
            os.chdir(original_dir)

    def run_migration_script(self, target_version):
        with open(self.get_migration_script_path(target_version), 'rb') as f:
            subprocess.check_call(
                ['sqlite3', self.get_version_file_path(target_version)],
                stdin=f
            )

    def describe_database_migration(self, target_version):
        message = 'Running migration script “{0}”...'
        print(message.format(self.get_migration_script_path(target_version)))


def main():
    Config.config_file_name = parse_args().config_file

    key_file = Config.get_config_value(Config.VALUE_DEPLOY_SIGNATURE_KEY_FILE)

    try:
        VersionDeployer(key_file).deploy_version()
    except DbDeploymentError as e:
        print(e.reason)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config-file',
        action='store',
        default='deploy-database.ini',
        help='config file name relative to “config” directory'
    )

    return parser.parse_args()


if __name__ == '__main__':
    main()

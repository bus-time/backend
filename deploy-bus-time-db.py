#!/usr/bin/python2
# coding: utf-8


from __future__ import absolute_import, unicode_literals, print_function
import ConfigParser
from getpass import getpass
import os
import subprocess
import tempfile
from zipfile import ZipFile

from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
import github3
import requests


class Config(object):
    CONFIG_FILE_DIR = 'config'
    CONFIG_FILE_NAME = 'deploy-bus-time-db.ini'
    CONFIG_SECTION_NAME = 'general'

    VALUE_REPO_OWNER = 'repo-owner'
    VALUE_REPO_NAME = 'repo-name'
    VALUE_REPO_BRANCH = 'repo-branch'
    VALUE_VERSION_TAG_NAME_PREFIX = 'version-tag-name-prefix'
    VALUE_DB_MAKE_TARGET = 'db-make-target'
    VALUE_DB_MADE_FILE_NAME = 'db-made-file-name'
    VALUE_DEPLOY_URL = 'deploy-url'
    VALUE_SIGNATURE_KEY_FILE = 'signature-key-file'

    @classmethod
    def get_config_value(cls, value_name):
        return cls.get_config_parser().get(cls.CONFIG_SECTION_NAME, value_name)

    @classmethod
    def get_config_parser(cls):
        config = ConfigParser.SafeConfigParser()
        config.read(cls.get_config_file_path())
        if not config.has_section(cls.CONFIG_SECTION_NAME):
            config.add_section(cls.CONFIG_SECTION_NAME)
        return config

    @classmethod
    def get_config_file_path(cls):
        return os.path.join(cls.get_config_dir_path(), cls.CONFIG_FILE_NAME)

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
    FORM_SIGNATURE_SUFFIX = '-signature'

    def __init__(self, key_file):
        self.signature_key = self.import_private_key(key_file)

    def import_private_key(self, key_file):
        return RSA.importKey(open(key_file, 'rb').read())

    def deploy_version(self):
        schema_version, commit_sha, content = DbFileMaker().make_db_file_info()
        self.deploy_database(schema_version, commit_sha, content)

    @describe(start='Deploying just built database file...', done='done.')
    def deploy_database(self, schema_version, commit_sha, contents):
        files = self.build_files_dict(schema_version, commit_sha, contents)
        deploy_url = Config.get_config_value(Config.VALUE_DEPLOY_URL)

        response = requests.post(deploy_url, files=files)

        if not response.ok:
            raise DbDeploymentError(self.build_error_text(response))

    def build_files_dict(self, schema_version, commit_sha, contents):
        files = {
            self.FORM_CONTENTS_KEY: contents,
            self.FORM_SCHEMA_VERSION_KEY: unicode(schema_version).encode(
                self.FORM_STRING_DATA_ENCODING),
            self.FORM_VERSION_KEY: commit_sha.encode(
                self.FORM_STRING_DATA_ENCODING)
        }

        signed_files = dict()
        for dict_key, data in files.items():
            self.append_file_to_dict(signed_files, dict_key, data)

        return signed_files

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


class DbFileMaker(object):
    ARCHIVE_FILE_NAME = 'archive.zip'
    ARCHIVE_FORMAT = 'zipball'
    EXTRACTED_ARCHIVE_DIR = 'archive'
    BRANCH_HEAD_REF_FORMAT = 'heads/{}'

    def make_db_file_info(self):
        repo = self.connect_to_repo()

        latest_schema_commit_info = self.get_latest_schema_commit_info(repo)
        if not latest_schema_commit_info:
            return None

        schema_version, schema_commit_sha = latest_schema_commit_info
        contents = self.build_database_contents(repo)

        return schema_version, schema_commit_sha, contents

    def connect_to_repo(self):
        username, password = self.get_credentials()
        return self.login_to_repo(username, password)

    def get_credentials(self):
        return raw_input('Username: '), getpass('Password: ')

    @describe(start='Logging in to repo...', done='done.')
    def login_to_repo(self, username, password):
        repo_owner = Config.get_config_value(Config.VALUE_REPO_OWNER)
        repo_name = Config.get_config_value(Config.VALUE_REPO_NAME)
        return github3.login(username, password).repository(repo_owner,
                                                            repo_name)

    def get_latest_schema_commit_info(self, repo):
        schema_version, commit_sha = self.get_latest_schema_tag_info(repo)
        self.describe_latest_schema_tag_info(schema_version, commit_sha)

        head_sha, branch_name = self.get_head_sha_info(repo)
        self.describe_head_sha(head_sha, branch_name)

        if commit_sha != head_sha:
            message = self.make_mismatching_sha_message(branch_name)
            raise DbDeploymentError(message)

        return schema_version, head_sha

    @describe(start='Obtaining latest tag with schema info...', done='done.')
    def get_latest_schema_tag_info(self, repo):
        tags = ((self.extract_schema_version(t), t.commit['sha'])
                for t in repo.iter_tags()
                if self.is_schema_version_tag(t))
        tags = sorted(tags, key=lambda (v, s): v, reverse=True)

        if len(tags) > 0:
            return tags[0]
        else:
            raise DbDeploymentError('No schema version tags found. ' +
                                    'Nothing to do.')

    def extract_schema_version(self, tag):
        name_prefix = Config.get_config_value(
            Config.VALUE_VERSION_TAG_NAME_PREFIX)
        return int(tag.name[len(name_prefix):])

    def is_schema_version_tag(self, tag):
        name_prefix = Config.get_config_value(
            Config.VALUE_VERSION_TAG_NAME_PREFIX)
        if not tag.name.startswith(name_prefix):
            return False

        try:
            self.extract_schema_version(tag)
        except TypeError:
            return False

        return True

    def describe_latest_schema_tag_info(self, schema_version, commit_sha):
        message = ("Latest schema version tag is of version {} and " +
                   "references commit “{}”.")
        print(message.format(schema_version, commit_sha))

    @describe(start='Obtaining HEAD SHA...', done='done.')
    def get_head_sha_info(self, repo):
        branch_name = Config.get_config_value(Config.VALUE_REPO_BRANCH)
        head = repo.ref(self.BRANCH_HEAD_REF_FORMAT.format(branch_name))

        if not head:
            raise DbDeploymentError(self.make_no_head_message(branch_name))

        return head.object.sha, branch_name

    def make_no_head_message(self, branch_name):
        message = ('No “{}” HEAD found. It seems the repo has no commits. ' +
                   'Nothing to do.')
        return message.format(branch_name)

    def describe_head_sha(self, head_sha, branch_name):
        print("Branch “{}” HEAD is “{}”.".format(branch_name, head_sha))

    def make_mismatching_sha_message(self, branch_name):
        message = ('Latest schema version tag does not reference “{}” HEAD.' +
                   'Nothing to do.')
        return message.format(branch_name)

    @describe(start='Building database contents...', done='done.')
    def build_database_contents(self, repo):
        download_dir = tempfile.mkdtemp()

        try:
            self.download_master_dir(repo, download_dir)
            database_file = self.make_database_file(download_dir)

            with open(database_file, 'rb') as f:
                return f.read()
        finally:
            self.cleanup(download_dir)

    def download_master_dir(self, repo, download_dir):
        archive_file = self.get_archive_file_name(download_dir)

        if not repo.archive(self.ARCHIVE_FORMAT, path=archive_file):
            raise RuntimeError('Error downloading the archive')

        ZipFile(archive_file).extractall(self.get_extracted_dir(download_dir))

    def get_archive_file_name(self, download_dir):
        return os.path.join(download_dir, self.ARCHIVE_FILE_NAME)

    def get_extracted_dir(self, download_dir):
        return os.path.join(download_dir, self.EXTRACTED_ARCHIVE_DIR)

    def make_database_file(self, download_dir):
        make_dir = self.get_make_dir(download_dir)
        make_target = Config.get_config_value(Config.VALUE_DB_MAKE_TARGET)
        db_file_name = Config.get_config_value(Config.VALUE_DB_MADE_FILE_NAME)

        subprocess.check_call(['make', make_target, '--directory', make_dir])
        return os.path.join(make_dir, db_file_name)

    def get_make_dir(self, download_dir):
        extracted_dir = self.get_extracted_dir(download_dir)
        return os.path.join(extracted_dir, os.listdir(extracted_dir)[0])

    def cleanup(self, download_dir):
        subprocess.check_call(['rm', '-rf', download_dir])


def main():
    key_file = Config.get_config_value(Config.VALUE_SIGNATURE_KEY_FILE)

    try:
        VersionDeployer(key_file).deploy_version()
    except DbDeploymentError as e:
        print(e.reason)


if __name__ == '__main__':
    main()

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


ARCHIVE_FILE_NAME = 'archive.zip'
ARCHIVE_FORMAT = 'zipball'
DOWNLOAD_DIR_PREFIX = 'bustime-backend-repo'
EXTRACTED_ARCHIVE_DIR = 'archive'
BRANCH_HEAD_REF_FORMAT = 'heads/{}'

FORM_STRING_DATA_ENCODING = 'utf8'
FORM_CONTENTS_KEY = 'contents'
FORM_VERSION_KEY = 'version'
FORM_SCHEMA_VERSION_KEY = 'schema-version'
FORM_SIGNATURE_SUFFIX = '-signature'


class Config(object):
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
        dir = os.path.abspath(cls.get_script_dir())
        return os.path.join(dir, cls.CONFIG_FILE_NAME)

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


def main():
    key_file = Config.get_config_value(Config.VALUE_SIGNATURE_KEY_FILE)
    deploy_version(key_file)


def deploy_version(key_file):
    repo = connect_to_repo()

    latest_schema_commit_info = get_latest_schema_commit_info(repo)
    if not latest_schema_commit_info:
        return
    schema_version, schema_commit_sha = latest_schema_commit_info

    deploy_database(schema_version, schema_commit_sha,
                    build_database_contents(repo),
                    key_file)


def connect_to_repo():
    username, password = get_credentials()
    return login_to_repo(username, password)


def get_credentials():
    return raw_input('Username: '), getpass('Password: ')


@describe(start='Logging in to repo...', done='done.')
def login_to_repo(username, password):
    repo_owner = Config.get_config_value(Config.VALUE_REPO_OWNER)
    repo_name = Config.get_config_value(Config.VALUE_REPO_NAME)
    return github3.login(username, password).repository(repo_owner, repo_name)


def get_latest_schema_commit_info(repo):
    schema_version, schema_version_commit_sha = get_latest_schema_tag_info(repo)
    describe_latest_schema_tag_info(schema_version, schema_version_commit_sha)
    if not schema_version or not schema_version_commit_sha:
        return None

    master_head_sha = get_master_head_sha(repo)
    describe_master_head_sha(master_head_sha)
    if not master_head_sha:
        return None

    if schema_version_commit_sha != master_head_sha:
        describe_schema_version_tag_not_master_head()
        return None

    return schema_version, master_head_sha


@describe(start='Obtaining latest tag with schema info...', done='done.')
def get_latest_schema_tag_info(repo):
    tags = ((extract_schema_version(t), t.commit['sha'])
            for t in repo.iter_tags()
            if is_schema_version_tag(t))
    tags = sorted(tags, key=lambda (v, s): v, reverse=True)

    if len(tags) > 0:
        return tags[0]
    else:
        return None, None


def extract_schema_version(tag):
    name_prefix = Config.get_config_value(Config.VALUE_VERSION_TAG_NAME_PREFIX)
    return int(tag.name[len(name_prefix):])


def is_schema_version_tag(tag):
    name_prefix = Config.get_config_value(Config.VALUE_VERSION_TAG_NAME_PREFIX)
    if not tag.name.startswith(name_prefix):
        return False

    try:
        extract_schema_version(tag)
    except TypeError:
        return False

    return True


def describe_latest_schema_tag_info(schema_version, schema_version_commit_sha):
    if not schema_version or not schema_version_commit_sha:
        print('No schema version tags found. Nothing to do.')
    else:
        message = ("Latest schema version tag is of version {} and " +
                   "references commit '{}'.")
        print(message.format(schema_version, schema_version_commit_sha))


@describe(start='Obtaining master HEAD sha...', done='done.')
def get_master_head_sha(repo):
    head = repo.ref(get_head_ref())
    if head:
        return head.object.sha
    else:
        return None


def get_head_ref():
    branch_name = Config.get_config_value(Config.VALUE_REPO_BRANCH)
    return BRANCH_HEAD_REF_FORMAT.format(branch_name)


def describe_master_head_sha(master_head_sha):
    if not master_head_sha:
        print('No master HEAD found. It seems the repo has no commits. ' +
              'Nothing to do.')
    else:
        print("Master HEAD is '{}'.".format(master_head_sha))


def describe_schema_version_tag_not_master_head():
    print('Latest schema version tag does not reference master HEAD. ' +
          'Nothing to do.')


@describe(start='Deploying just built database file...', done='done.')
def deploy_database(schema_version, master_head_sha, contents, key_file):
    files = build_files_dict(schema_version, master_head_sha, contents,
                             key_file)
    deploy_url = Config.get_config_value(Config.VALUE_DEPLOY_URL)
    response = requests.post(deploy_url, files=files)
    if not response.ok:
        print_response_error(response)


def build_files_dict(schema_version, master_head_sha, contents, key_file):
    signature_key = import_private_key(key_file)

    files = {
        FORM_CONTENTS_KEY: contents,
        FORM_SCHEMA_VERSION_KEY: unicode(schema_version).encode(
            FORM_STRING_DATA_ENCODING),
        FORM_VERSION_KEY: master_head_sha.encode(FORM_STRING_DATA_ENCODING)
    }

    signed_files = dict()
    for dict_key, data in files.items():
        append_file_to_dict(signed_files, dict_key, data, signature_key)

    return signed_files


def import_private_key(key_file):
    return RSA.importKey(open(key_file, 'rb').read())


def append_file_to_dict(dict, dict_key, data, signature_key):
    dict_signature_key = '{}{}'.format(dict_key, FORM_SIGNATURE_SUFFIX)

    dict[dict_key] = data
    dict[dict_signature_key] = make_signature(data, signature_key)


def make_signature(data, key):
    sha = SHA512.new()
    sha.update(data)

    return PKCS1_PSS.new(key).sign(sha)


def print_response_error(response):
    print('Error {} {}'.format(response.status_code, response.reason))
    print(response.text)


@describe(start='Building database contents...', done='done.')
def build_database_contents(repo):
    download_dir = get_download_dir()

    try:
        download_master_dir(repo, download_dir)
        database_file = make_database_file(download_dir)

        with open(database_file, 'rb') as f:
            return f.read()
    finally:
        cleanup(download_dir)


def get_download_dir():
    return tempfile.mkdtemp(prefix=DOWNLOAD_DIR_PREFIX)


def download_master_dir(repo, download_dir):
    archive_file = get_archive_file_name(download_dir)

    if not repo.archive(ARCHIVE_FORMAT, path=archive_file):
        raise RuntimeError('Error downloading the archive')

    ZipFile(archive_file).extractall(get_extracted_dir(download_dir))


def get_archive_file_name(download_dir):
    return os.path.join(download_dir, ARCHIVE_FILE_NAME)


def get_extracted_dir(download_dir):
    return os.path.join(download_dir, EXTRACTED_ARCHIVE_DIR)


def make_database_file(download_dir):
    make_dir = get_make_dir(download_dir)
    make_target = Config.get_config_value(Config.VALUE_DB_MAKE_TARGET)
    db_file_name = Config.get_config_value(Config.VALUE_DB_MADE_FILE_NAME)

    subprocess.check_call(['make', make_target, '--directory', make_dir])
    return os.path.join(make_dir, db_file_name)


def get_make_dir(download_dir):
    extracted_dir = get_extracted_dir(download_dir)
    return os.path.join(extracted_dir, os.listdir(extracted_dir)[0])


def cleanup(download_dir):
    subprocess.check_call(['rm', '-rf', download_dir])


if __name__ == '__main__':
    main()

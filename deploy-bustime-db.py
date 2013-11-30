#!/usr/bin/python2
# coding: utf-8


from __future__ import absolute_import, unicode_literals, print_function
from getpass import getpass
import os
import subprocess
import tempfile
from zipfile import ZipFile

import github3
import requests


ARCHIVE_FILE_NAME = 'archive.zip'
ARCHIVE_FORMAT = 'zipball'
DB_FILE_NAME = 'bustime.db.gz'
DOWNLOAD_DIR_PREFIX = 'bustime-backend-repo'
EXTRACTED_ARCHIVE_DIR = 'archive'
MAKE_TARGET = 'release'
MASTER_HEAD_REF = 'heads/master'
REPO_NAME = 'bus-time-database'
REPO_OWNER = 'win2l'
VERSION_TAG_NAME_PREFIX = 'db-schema-version-'

DEPLOY_URL = 'http://bustime-backend-dsav.herokuapp.com/db-updates/deploy'
FORM_STRING_DATA_ENCODING = 'utf8'
FORM_CONTENTS_KEY = 'contents'
FORM_VERSION_KEY = 'version'
FORM_SCHEMA_VERSION_KEY = 'schema-version'


def deploy_version():
    repo = connect_to_repo()

    latest_schema_commit_info = get_latest_schema_commit_info(repo)
    if not latest_schema_commit_info:
        return
    schema_version, schema_commit_sha = latest_schema_commit_info

    deploy_database(schema_version, schema_commit_sha,
                    build_database_contents(repo))


def describe(start=None, done=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(start or '', end=' ')

            try:
                result = func(*args, **kwargs)
                print(done or '')
                return result
            except:
                print('')
                raise

        return wrapper

    return decorator


def connect_to_repo():
    username, password = get_credentials()
    return login_to_repo(username, password)


def get_credentials():
    return raw_input('Username: '), getpass('Password: ')


@describe(start='Logging in to repo...', done='done.')
def login_to_repo(username, password):
    return github3.login(username, password).repository(REPO_OWNER, REPO_NAME)


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
    return int(tag.name[len(VERSION_TAG_NAME_PREFIX):])


def is_schema_version_tag(tag):
    if not tag.name.startswith(VERSION_TAG_NAME_PREFIX):
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
    head = repo.ref(MASTER_HEAD_REF)
    if head:
        return head.object.sha
    else:
        return None


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
def deploy_database(schema_version, master_head_sha, contents):
    files = {
        FORM_CONTENTS_KEY: contents,
        FORM_SCHEMA_VERSION_KEY: unicode(schema_version).encode(
            FORM_STRING_DATA_ENCODING),
        FORM_VERSION_KEY: master_head_sha.encode(FORM_STRING_DATA_ENCODING)
    }

    response = requests.post(DEPLOY_URL, files=files)
    if not response.ok:
        print_response_error(response)


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
    subprocess.check_call(['make', MAKE_TARGET, '--directory', make_dir])
    return os.path.join(make_dir, DB_FILE_NAME)


def get_make_dir(download_dir):
    extracted_dir = get_extracted_dir(download_dir)
    return os.path.join(extracted_dir, os.listdir(extracted_dir)[0])


def cleanup(download_dir):
    subprocess.check_call(['rm', '-rf', download_dir])


if __name__ == '__main__':
    deploy_version()

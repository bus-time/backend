# coding: utf-8


from __future__ import absolute_import, unicode_literals, print_function
from getpass import getpass
import os
import tempfile
from zipfile import ZipFile

from github3 import login
import sh

from backend.db import Database, db_session
from backend.util import Config


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


def deploy_version():
    repo = connect_to_repo()

    schema_version, schema_version_commit_sha = get_latest_schema_tag(repo)
    describe_latest_schema_tag(schema_version, schema_version_commit_sha)
    if not schema_version or not schema_version_commit_sha:
        return

    master_head_sha = get_master_head_sha(repo)
    describe_master_head_sha(master_head_sha)
    if not master_head_sha:
        return

    if schema_version_commit_sha != master_head_sha:
        describe_schema_version_not_master_head()
        return

    database = get_latest_deployed_database()
    describe_latest_deployed_database(database)

    if database and database.schema_version > schema_version:
        describe_more_recent_schema_deployed(database, schema_version)
        return

    if database and database.version == master_head_sha:
        describe_version_already_deployed(database)
        return

    if database and database.schema_version != schema_version:
        database = None

    save_database_data(database, schema_version, master_head_sha,
                       build_database_contents(repo))


def describer(start=None, done=None):
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


@describer(start='Logging in to repo...', done='done.')
def login_to_repo(username, password):
    return login(username, password).repository(REPO_OWNER, REPO_NAME)


def get_credentials():
    return raw_input('Username: '), getpass('Password: ')


@describer(start='Obtaining latest tag with schema info...', done='done.')
def get_latest_schema_tag(repo):
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


def describe_latest_schema_tag(schema_version, schema_version_commit_sha):
    if not schema_version or not schema_version_commit_sha:
        print('No schema version tags found. Nothing to do.')
    else:
        message = ("Latest schema version tag is of version {} and " +
                   "references commit '{}'.")
        print(message.format(schema_version, schema_version_commit_sha))


@describer(start='Obtaining master HEAD sha...', done='done.')
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


def describe_schema_version_not_master_head():
    print('Latest schema version tag does not reference master HEAD. ' +
          'Nothing to do.')


@describer(start='Getting currently latest deployed database...', done='done.')
def get_latest_deployed_database():
    return (Database.query
            .order_by(Database.schema_version.desc())
            .first())


def describe_latest_deployed_database(database):
    if not database:
        print('No deployed database found.')
    else:
        message = ("Latest deployed database has schema version {} and is of " +
                   "version '{}'")
        print(message.format(database.schema_version, database.version))


def describe_more_recent_schema_deployed(database, schema_version):
    message = ('Database of schema version {} can not be deployed because ' +
               'more recent version {} is already deployed. Nothing to do.')
    print(message.format(schema_version, database.schema_version))


def describe_version_already_deployed(database):
    print("Database of version '{}' is already deployed. Nothing to do."
    .format(database.version))


@describer(start='Building database contents...', done='done.')
def build_database_contents(repo):
    download_dir = get_dowload_dir()

    try:
        download_master_dir(repo, download_dir)
        database_file = make_database_file(download_dir)

        with open(database_file, 'rb') as f:
            return f.read()
    finally:
        cleanup(download_dir)


def get_dowload_dir():
    base_dir = Config.get_config_value(Config.VALUE_DB_REPO_DOWNLOAD_DIR)
    base_dir = os.path.realpath(base_dir)
    return tempfile.mkdtemp(dir=base_dir, prefix=DOWNLOAD_DIR_PREFIX)


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
    initial_dir = os.getcwd()
    make_dir = get_make_dir(download_dir)

    try:
        os.chdir(make_dir)
        sh.make(MAKE_TARGET)
        return os.path.join(make_dir, DB_FILE_NAME)
    finally:
        os.chdir(initial_dir)


def get_make_dir(download_dir):
    extracted_dir = get_extracted_dir(download_dir)
    return os.path.join(extracted_dir, os.listdir(extracted_dir)[0])


def cleanup(download_dir):
    sh.rm('-rf', download_dir)


@describer(start='Saving just built database file...', done='done.')
def save_database_data(database, schema_version, version, contents):
    if not database:
        database = Database(schema_version=schema_version)

    database.version = version
    database.contents = contents

    db_session.add(database)
    db_session.commit()

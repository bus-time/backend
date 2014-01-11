# coding: utf-8


from __future__ import absolute_import, unicode_literals
import glob
import httplib
import itertools
import os

from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from flask import jsonify, url_for, make_response, request
from werkzeug.exceptions import abort

from backend.server import app
from backend.db import Database, db_session
from backend.util import Config


CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=file.db.gz'

FORM_STRING_DATA_ENCODING = 'utf8'
FORM_CONTENTS_KEY = 'contents'
FORM_VERSION_KEY = 'version'
FORM_SCHEMA_VERSION_KEY = 'schema-version'
FORM_SIGNATURE_SUFFIX = '-signature'

SCHEMA_VERSION_MIN = 1
SCHEMA_VERSION_MAX = 2 ** 16

ERROR_MORE_RECENT_SCHEMA_DEPLOYED = 'More recent schema deployed'
ERROR_VERSION_ALREADY_DEPLOYED = 'Version is already deployed'
ERROR_INVALID_SCHEMA_VERSION = 'Invalid schema version specified'
ERROR_NOT_ALL_FORM_FIELDS = 'Not all form fields specified'
ERROR_AUTHENTICATION_FAILED = 'Authentication failed'

DEPLOYMENT_KEY_EXT = 'pub'


@app.route('/databases/<int:schema_version>')
def database_info(schema_version):
    database = (Database.query
                .filter(Database.schema_version == schema_version)
                .first())

    if not database:
        abort(httplib.NOT_FOUND)

    return jsonify(build_version_info_dict(database))


def build_version_info_dict(database):
    return {
        'schema_version': database.schema_version,
        'version': database.version
    }


@app.route('/databases/<int:schema_version>/content')
def database_content(key):
    database = (Database.query
                .filter(Database.schema_version == schema_version)
                .first())

    if not database:
        abort(httplib.NOT_FOUND)

    return build_db_contents_response(database.contents)


def build_db_contents_response(contents):
    response = make_response(contents)
    response.headers['Content-Type'] = CONTENT_TYPE_OCTET_STREAM
    response.headers['Content-Disposition'] = CONTENT_DISPOSITION_DB_FILE
    return response


@app.route('/databases', methods=['POST'])
def database_deploy():
    try:
        contents, schema_version, version = read_deploy_data(request)
        update_database(contents, schema_version, version)
    except DeployDataError as e:
        return make_error_response(e.error,
                                   httplib.BAD_REQUEST)
    except DeployConfictError as e:
        return make_error_response(e.error, httplib.CONFLICT)
    except DeployAuthenticationError as e:
        return make_error_response(ERROR_AUTHENTICATION_FAILED,
                                   httplib.UNAUTHORIZED)

    return database_info(schema_version)


def read_deploy_data(request):
    files = read_signed_files(request, (FORM_CONTENTS_KEY,
                                        FORM_SCHEMA_VERSION_KEY,
                                        FORM_VERSION_KEY))

    contents = files[FORM_CONTENTS_KEY]
    schema_version = read_schema_version(files)
    version = read_form_string_data(files, FORM_VERSION_KEY)

    return contents, schema_version, version


def read_signed_files(request, keys):
    signed_file_pairs = {k: build_signed_file_pair(request, k) for k in keys}
    verify_signed_file_pairs(signed_file_pairs)
    return {k: signed_file_pairs[k][0] for k in signed_file_pairs.keys()}


def build_signed_file_pair(request, key):
    signature_key = '{}{}'.format(key, FORM_SIGNATURE_SUFFIX)

    if not key in request.files or not signature_key in request.files:
        raise DeployDataError(ERROR_NOT_ALL_FORM_FIELDS)

    return (request.files[key].stream.read(),
            request.files[key + FORM_SIGNATURE_SUFFIX].stream.read())


def verify_signed_file_pairs(pairs):
    if len(pairs) == 0:
        return True

    public_key = get_matched_public_key(pairs.itervalues().next())
    if not public_key:
        raise DeployAuthenticationError()

    for pair in itertools.islice(pairs.itervalues(), 1):
        if not is_signed_file_authentic(pair, public_key):
            raise DeployAuthenticationError()


def get_matched_public_key(pair):
    for key in get_public_keys():
        if is_signed_file_authentic(pair, key):
            return key

    return None


def get_public_keys():
    key_file_mask = os.path.join(Config.get_deployment_key_dir(),
                                 '*.{}'.format(DEPLOYMENT_KEY_EXT))
    for key_file in glob.glob(key_file_mask):
        yield import_public_key(key_file)


def import_public_key(key_file):
    return RSA.importKey(open(key_file, 'rb').read())


def is_signed_file_authentic(pair, key):
    data, signature = pair

    sha = SHA512.new()
    sha.update(data)

    return PKCS1_PSS.new(key).verify(sha, signature)


def read_schema_version(files):
    try:
        schema_version_str = read_form_string_data(
            files, FORM_SCHEMA_VERSION_KEY)
        schema_version_int = int(schema_version_str)
    except ValueError:
        raise DeployDataError(ERROR_INVALID_SCHEMA_VERSION)

    if not (SCHEMA_VERSION_MIN <= schema_version_int <= SCHEMA_VERSION_MAX):
        raise DeployDataError(ERROR_INVALID_SCHEMA_VERSION)

    return schema_version_int


def read_form_string_data(files, key):
    return files[key].decode(FORM_STRING_DATA_ENCODING)


def update_database(contents, schema_version, version):
    database = get_latest_deployed_database()

    check_database_conflicts(database, schema_version, version)

    if database and database.schema_version == schema_version:
        delete_database(database)
    create_database(contents, schema_version, version)

    db_session.commit()


def check_database_conflicts(database, schema_version, version):
    if database and database.schema_version > schema_version:
        raise DeployConfictError(ERROR_MORE_RECENT_SCHEMA_DEPLOYED)
    if database and database.version == version:
        raise DeployConfictError(ERROR_VERSION_ALREADY_DEPLOYED)


def delete_database(database):
    db_session.delete(database)
    db_session.flush()


def create_database(contents, schema_version, version):
    database = Database(schema_version=schema_version,
                        version=version,
                        contents=contents)
    db_session.add(database)


def make_error_response(error, code):
    response = {
        'error': error
    }

    return jsonify(response), code


def get_latest_deployed_database():
    return (Database.query
            .order_by(Database.schema_version.desc())
            .first())


class DeployDataError(ValueError):
    def __init__(self, error):
        self.error = error


class DeployConfictError(ValueError):
    def __init__(self, error):
        self.error = error


class DeployAuthenticationError(ValueError):
    pass

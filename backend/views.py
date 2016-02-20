# coding: utf-8


import glob
import itertools
import collections
import http.client as http
import os

from Crypto.Hash import SHA512, SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
import flask
from werkzeug import exceptions as wzex

from backend import db, util
from backend.server import app


@app.route('/databases/<int:schema_version>')
def database_info(schema_version):
    database = find_database(schema_version)
    return HttpUtils.build_database_info_response(database)


@app.route('/databases/<int:schema_version>/contents')
def database_contents(schema_version):
    database = find_database(schema_version)
    return HttpUtils.build_database_contents_response(database)


def find_database(schema_version):
    database = db.Database.find_by_schema_version(schema_version)

    if not database:
        wzex.abort(http.NOT_FOUND)

    return database


@app.route('/databases', methods=['POST'])
def database_deploy():
    try:
        schema_version = Deployer().deploy_database(flask.request.files)
    except DeployDataError as e:
        return HttpUtils.make_error_response(e.error, http.BAD_REQUEST)
    except DeployConfictError as e:
        return HttpUtils.make_error_response(e.error, http.CONFLICT)
    except DeployAuthenticationError as e:
        return HttpUtils.make_error_response(e.error, http.UNAUTHORIZED)

    return database_info(schema_version)


class HttpUtils(object):
    HEADER_CONTENT_TYPE = 'Content-Type'
    HEADER_CONTENT_DISPOSITION = 'Content-Disposition'
    HEADER_X_CONTENT_SHA256 = 'X-Content-SHA256'

    CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
    CONTENT_DISPOSITION_DB_FILE = 'attachment; filename=bus-time.db'

    @classmethod
    def build_database_info_response(cls, database):
        version_info_dict = {
            'schema_version': database.schema_version,
            'version': database.version
        }

        return flask.jsonify(version_info_dict)

    @classmethod
    def build_database_contents_response(cls, database):
        response = flask.make_response(database.contents)

        headers = cls.build_extra_contents_headers(database.contents)
        for name, value in headers.items():
            response.headers[name] = value

        return response

    @classmethod
    def build_extra_contents_headers(cls, contents):
        return {
            cls.HEADER_CONTENT_TYPE: cls.CONTENT_TYPE_OCTET_STREAM,
            cls.HEADER_CONTENT_DISPOSITION: cls.CONTENT_DISPOSITION_DB_FILE,
            cls.HEADER_X_CONTENT_SHA256: cls.calc_contents_sha256(contents)
        }

    @classmethod
    def calc_contents_sha256(cls, contents):
        sha = SHA256.new()
        sha.update(contents)
        return sha.hexdigest()

    @classmethod
    def make_error_response(cls, error, code):
        response = {
            'error': error
        }

        return flask.jsonify(response), code


class Deployer(object):
    FORM_STRING_DATA_ENCODING = 'utf8'
    FORM_CONTENTS_KEY = 'contents'
    FORM_VERSION_KEY = 'version'
    FORM_SCHEMA_VERSION_KEY = 'schema-version'
    FORM_IS_MIGRATION_UPDATE_KEY = 'is-migration-update'
    FORM_VALUE_TRUE = 'true'
    FORM_VALUE_FALSE = 'false'
    FORM_SIGNATURE_SUFFIX = '-signature'

    DEPLOYMENT_KEY_EXT = 'pub'

    ERROR_NOT_ALL_FORM_FIELDS = 'Not all form fields specified'
    ERROR_INVALID_SCHEMA_VERSION = 'Invalid schema version specified'
    ERROR_MORE_RECENT_SCHEMA_DEPLOYED = 'More recent schema deployed'
    ERROR_VERSION_ALREADY_DEPLOYED = 'Version is already deployed'

    SCHEMA_VERSION_MIN = 1
    SCHEMA_VERSION_MAX = 2 ** 16

    SignedFile = collections.namedtuple('SignedFile', ['data', 'signature'])

    def deploy_database(self, files):
        (contents, schema_version,
         version, override_same_version) = self.read_deploy_data(files)

        self.update_database(contents, schema_version, version,
                             override_same_version)

        return schema_version

    def read_deploy_data(self, files):
        files = self.read_signed_files(
            files,
            (self.FORM_CONTENTS_KEY,
             self.FORM_SCHEMA_VERSION_KEY,
             self.FORM_VERSION_KEY,
             self.FORM_IS_MIGRATION_UPDATE_KEY)
        )

        contents = files[self.FORM_CONTENTS_KEY]
        schema_version = self.read_schema_version(files)
        version = self.read_form_string_data(files, self.FORM_VERSION_KEY)
        is_migration_update = self.read_form_bool_data(
            files, self.FORM_IS_MIGRATION_UPDATE_KEY
        )

        return contents, schema_version, version, is_migration_update

    def read_signed_files(self, files, keys):
        signed_files = {k: self.build_signed_files(files, k) for k in keys}
        self.verify_signed_files(signed_files)
        return {k: signed_files[k].data for k in signed_files.keys()}

    def build_signed_files(self, files, key):
        signature_key = '{}{}'.format(key, self.FORM_SIGNATURE_SUFFIX)

        if not key in files or not signature_key in files:
            raise DeployDataError(self.ERROR_NOT_ALL_FORM_FIELDS)

        return self.SignedFile(
            files[key].stream.read(),
            files[key + self.FORM_SIGNATURE_SUFFIX].stream.read()
        )

    def verify_signed_files(self, signed_files):
        if len(signed_files) == 0:
            return

        signed_files = iter(signed_files.values())

        public_key = self.find_public_key(next(signed_files))
        if not public_key:
            raise DeployAuthenticationError()

        for signed_file in itertools.islice(signed_files, 1):
            if not self.is_signed_file_authentic(signed_file, public_key):
                raise DeployAuthenticationError()

    def find_public_key(self, signed_file):
        for key in self.get_public_keys():
            if self.is_signed_file_authentic(signed_file, key):
                return key

        return None

    def get_public_keys(self):
        key_file_mask = os.path.join(
            util.Config.get().deployment_key_dir,
            '*.{}'.format(self.DEPLOYMENT_KEY_EXT)
        )
        for key_file in glob.glob(key_file_mask):
            yield self.import_public_key(key_file)

    def import_public_key(self, key_file):
        return RSA.importKey(open(key_file, 'rb').read())

    def is_signed_file_authentic(self, signed_file, key):
        sha = SHA512.new()
        sha.update(signed_file.data)

        return PKCS1_PSS.new(key).verify(sha, signed_file.signature)

    def read_schema_version(self, files):
        try:
            schema_version_str = self.read_form_string_data(
                files, self.FORM_SCHEMA_VERSION_KEY)
            schema_version_int = int(schema_version_str)
        except ValueError:
            raise DeployDataError(self.ERROR_INVALID_SCHEMA_VERSION)

        if not self.in_range(schema_version_int,
                             self.SCHEMA_VERSION_MIN,
                             self.SCHEMA_VERSION_MAX):
            raise DeployDataError(self.ERROR_INVALID_SCHEMA_VERSION)

        return schema_version_int

    def in_range(self, value, range_min, range_max):
        return range_min <= value <= range_max

    def read_form_string_data(self, files, key):
        return files[key].decode(self.FORM_STRING_DATA_ENCODING)

    def read_form_bool_data(self, files, key):
        return self.form_value_to_bool(self.read_form_string_data(files, key))

    def form_value_to_bool(self, value):
        if value == self.FORM_VALUE_TRUE:
            return True
        elif value == self.FORM_VALUE_FALSE:
            return False
        else:
            raise ValueError(value)

    def update_database(self, contents, schema_version, version,
                        is_migration_update):
        latest_database = db.Database.find_latest()
        self.check_database_conflicts(latest_database, schema_version, version,
                                      is_migration_update)

        same_schema_database = db.Database.find_by_schema_version(
            schema_version
        )
        if same_schema_database:
            self.delete_database(same_schema_database)

        self.create_database(contents, schema_version, version)

        db.database_session.commit()

    def check_database_conflicts(self, latest_database, schema_version, version,
                                 is_migration_update):
        if not latest_database:
            return

        if is_migration_update:
            return

        if latest_database.schema_version > schema_version:
            raise DeployConfictError(self.ERROR_MORE_RECENT_SCHEMA_DEPLOYED)

        if self.is_same_version(latest_database, schema_version, version):
            raise DeployConfictError(self.ERROR_VERSION_ALREADY_DEPLOYED)

    def is_same_version(self, latest_database, schema_version, version):
        return (latest_database.schema_version == schema_version
                and latest_database.version == version)

    def delete_database(self, database):
        db.database_session.delete(database)
        db.database_session.flush()

    def create_database(self, contents, schema_version, version):
        database = db.Database(schema_version=schema_version,
                               version=version,
                               contents=contents)
        db.database_session.add(database)


class DeployDataError(ValueError):
    def __init__(self, error):
        super().__init__()
        self.error = error


class DeployConfictError(ValueError):
    def __init__(self, error):
        super().__init__()
        self.error = error


class DeployAuthenticationError(ValueError):
    error = 'Authentication failed'

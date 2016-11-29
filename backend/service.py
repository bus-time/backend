# coding: utf-8


import abc
import base64
import codecs
import collections
import json

from cryptography import exceptions as crypto_exceptions
from cryptography.hazmat.backends import default_backend as crypto_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives import serialization as crypto_serial
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding

from backend import db, config


class DatabaseQuery:
    def get_version(self, schema_version):
        with db.Session() as session:
            database = self._find_database(session, schema_version)
            if not database:
                raise NoDatabaseFound()
            return database.version

    def _find_database(self, session, schema_version):
        return (session.query(db.Database)
                .filter(db.Database.schema_version == schema_version)
                .first())

    def get_content(self, schema_version):
        with db.Session() as session:
            database = self._find_database(session, schema_version)
            if not database:
                raise NoDatabaseFound()

            return database.content


class NoDatabaseFound(RuntimeError):
    pass


class Base64:
    ASCII_ENCODING = 'ascii'

    @classmethod
    def binary_to_base64_str(cls, binary):
        if binary is None:
            return None

        return base64.b64encode(binary).decode(cls.ASCII_ENCODING)

    @classmethod
    def base64_str_to_binary(cls, base64_str):
        if base64_str is None:
            return None

        return base64.b64decode(base64_str.encode(cls.ASCII_ENCODING))


class SignatureVerifier:
    UTF8_ENCODING = 'utf-8'

    def verify(self, public_key_binaries, text_to_verify, signature):
        if not signature:
            return False

        binary_to_verify = text_to_verify.encode(self.UTF8_ENCODING)

        for public_key_binary in public_key_binaries:
            if self._verify_single(
                public_key_binary, binary_to_verify, signature
            ):
                return True

        return False

    def _verify_single(self, public_key_binary, binary_to_verify, signature):
        verifier = self._build_verifier(public_key_binary, signature)
        verifier.update(binary_to_verify)

        try:
            verifier.verify()
            return True
        except crypto_exceptions.InvalidSignature:
            return False

    def _build_verifier(self, public_key_binary, signature):
        return self._load_public_key(public_key_binary).verifier(
            signature,
            # Stay with PKCS1 v1.5 padding since PSS is not as widely spread
            # and is not implemented in many libraries
            crypto_padding.PKCS1v15(),
            crypto_hashes.SHA512()
        )

    def _load_public_key(self, public_key_binary):
        return crypto_serial.load_ssh_public_key(
            public_key_binary, crypto_backend()
        )


SchemaVersionContent = collections.namedtuple(
    'SchemaVersionContent', 'schema_version, content'
)


class InvalidUpdateContentError(RuntimeError):
    def __init__(self, message):
        self.message = message


class DatabaseUpdateContentValidator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def validate(self, update_content):
        pass


class VersionValidator(DatabaseUpdateContentValidator):
    VERSION_LENGTH = 40
    ALLOWED_CHARS = '01234567890abcdef'

    def validate(self, update_content):
        version = update_content.version

        if not isinstance(version, str):
            raise InvalidUpdateContentError('Version is not a string')

        if len(version) != self.VERSION_LENGTH:
            raise InvalidUpdateContentError(
                'Version length is not 40 characters'
            )

        for char in version:
            if char not in self.ALLOWED_CHARS:
                raise InvalidUpdateContentError(
                    'Version contains invalid characters'
                )


class SchemaVersionValidator(DatabaseUpdateContentValidator):
    SCHEMA_VERSION_MIN = 1
    SCHEMA_VERSION_MAX = 2 ** 16

    def __init__(self):
        self._schema_versions = set()

    def validate(self, update_content):
        self._schema_versions.clear()

        for content_schema_version in update_content.schema_versions:
            self._validate_schema_version(
                content_schema_version.schema_version
            )

    def _validate_schema_version(self, schema_version):
        if not isinstance(schema_version, int):
            raise InvalidUpdateContentError('Schema version is not an integer')

        if not self._in_range(
            schema_version, self.SCHEMA_VERSION_MIN, self.SCHEMA_VERSION_MAX
        ):
            raise InvalidUpdateContentError(
                'Schema version does not fall into required range'
            )

        self._validate_uniqueness(schema_version)

    def _in_range(self, value, range_min, range_max):
        return range_min <= value <= range_max

    def _validate_uniqueness(self, schema_version):
        if schema_version in self._schema_versions:
            raise InvalidUpdateContentError('Schema versions are not unique')

        self._schema_versions.add(schema_version)


class ContentValidator(DatabaseUpdateContentValidator):
    def validate(self, update_content):
        for content_schema_version in update_content.schema_versions:
            self._validate_content(content_schema_version.content)

    def _validate_content(self, content):
        if not isinstance(content, bytes):
            raise InvalidUpdateContentError('Content is not a byte sequence')

        if len(content) <= 0:
            raise InvalidUpdateContentError('Content is empty')


class DatabaseUpdateContent:
    def __init__(self, update_content_json):
        try:
            update_content_dict = json.loads(update_content_json)

            self.version = update_content_dict['version']
            self.schema_versions = self._parse_schema_versions(
                update_content_dict['schema_versions']
            )
        except:
            raise InvalidUpdateContentError('Invalid content JSON')

        self._validate()

    def _parse_schema_versions(self, schema_version_list):
        return [self._parse_schema_version(x) for x in schema_version_list]

    def _parse_schema_version(self, schema_version_dict):
        return SchemaVersionContent(
            schema_version=schema_version_dict['schema_version'],
            content=Base64.base64_str_to_binary(schema_version_dict['content'])
        )

    def _validate(self):
        validators = [
            VersionValidator(),
            SchemaVersionValidator(),
            ContentValidator()
        ]

        for validator in validators:
            validator.validate(self)


class InvalidSignatureError(RuntimeError):
    pass


class DatabaseUpdate:
    def get_update_content(self, update_content_json, signature_text):
        signature = Base64.base64_str_to_binary(signature_text)
        if not self._is_signature_valid(update_content_json, signature):
            raise InvalidSignatureError()

        return DatabaseUpdateContent(update_content_json)

    def _is_signature_valid(self, update_content_json, signature):
        return SignatureVerifier().verify(
            config.Config.get().key_binaries,
            update_content_json,
            Base64.base64_str_to_binary(signature)
        )

    def apply_update(self, update_content):
        with db.Session() as session:
            existing_databases = self._fetch_existing_databases(
                session, update_content
            )

            for schema_version_content in update_content.schema_versions:
                self._single_apply_update(
                    session,
                    existing_databases,
                    schema_version_content,
                    update_content.version
                )

        session.commit()

    def _fetch_existing_databases(self, session, update_content):
        schema_versions = [
            x.schema_version for x in update_content.schema_versions
        ]

        return (session
            .query(db.Database)
            .filter(db.Database.schema_version.in_(schema_versions))
            .all()
        )

    def _single_apply_update(self, session, existing_databases,
                             schema_version_content, version):
        existing_database = self._find_existing_database(
            existing_databases, schema_version_content.schema_version
        )

        if existing_database:
            existing_database.version = version
            existing_database.contents = schema_version_content.content
        else:
            self._create_new_database(
                session, schema_version_content, version
            )

    def _find_existing_database(self, existing_databases, schema_version):
        return next(
            (x for x in existing_databases
             if x.schema_version == schema_version),
            None
        )

    def _create_new_database(self, session, schema_version_content, version):
        new_database = db.Database(
            version=version,
            schema_version=schema_version_content.schema_version,
            content=schema_version_content.content
        )
        session.add(new_database)


class Sha256:
    HEX_ENCODING = 'hex'
    ASCII_ENCODING = 'ascii'

    def make_hash(self, binary):
        sha256 = crypto_hashes.Hash(
            crypto_hashes.SHA256(), backend=crypto_backend()
        )
        sha256.update(binary)
        digest_binary = sha256.finalize()

        hex_binary = codecs.encode(digest_binary, self.HEX_ENCODING)
        return hex_binary.decode(self.ASCII_ENCODING)

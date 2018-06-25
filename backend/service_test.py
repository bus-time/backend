# coding: utf-8


import base64
import collections
import json
import tempfile

import pytest
from cryptography.hazmat.backends import default_backend as crypto_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes
from cryptography.hazmat.primitives import serialization as crypto_serial
from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa

from backend import db, config, service


class SqliteDbConfig(config.Config):
    SQLITE_DB_URL = 'sqlite:///{0}'

    def __init__(self):
        self._db_url = self.SQLITE_DB_URL.format(self._get_temp_file_name())

    def _get_temp_file_name(self):
        with tempfile.NamedTemporaryFile() as f:
            return f.name

    @property
    def db_url(self):
        return self._db_url

    @property
    def key_binaries(self):
        return None


class BaseDbAwareTest:
    MIN_VERSION = 1
    MAX_VERSION = 5

    def init_filled_database(self):
        databases = [
            db.Database(schema_version=x, version=str(x), content=bytes(x))
            for x in range(self.MIN_VERSION, self.MAX_VERSION + 1)
        ]
        self.init_database(databases)

    def init_database(self, databases):
        is_new_database = not isinstance(config.Config.get(), SqliteDbConfig)
        if is_new_database:
            config.Config.init(SqliteDbConfig())

        with db.Session(init_schema=is_new_database) as session:
            session.query(db.Database).delete()
            for x in databases:
                session.add(x)


class TestDatabaseQuery(BaseDbAwareTest):
    def test_get_existing_version_info_succeeds(self):
        self.init_filled_database()
        version = service.DatabaseQuery().get_version(self.MIN_VERSION)
        assert version == str(self.MIN_VERSION)

    def test_get_non_existing_version_info_fails(self):
        self.init_filled_database()

        with pytest.raises(service.NoDatabaseFound):
            service.DatabaseQuery().get_version(
                self.MAX_VERSION + 1
            )

    def test_get_existing_content_succeeds(self):
        self.init_filled_database()
        content = service.DatabaseQuery().get_content(self.MIN_VERSION)
        assert content == bytes(self.MIN_VERSION)

    def test_get_non_existing_content_fails(self):
        self.init_filled_database()

        with pytest.raises(service.NoDatabaseFound):
            service.DatabaseQuery().get_content(self.MAX_VERSION + 1)


class TestBase64:
    def test_encode_succeeds(self):
        assert service.Base64.binary_to_base64_str(b'1') == 'MQ=='

    def test_decode_succeeds(self):
        assert service.Base64.base64_str_to_binary('MQ==') == b'1'

    def test_none_yields_empty(self):
        assert service.Base64.binary_to_base64_str(None) is None
        assert service.Base64.base64_str_to_binary(None) is None

    def test_empty_yields_empty(self):
        assert service.Base64.binary_to_base64_str(b'') == ''
        assert service.Base64.base64_str_to_binary('') == b''


class TestDatabaseUpdateContent:
    def test_simple_content_succeeds(self):
        content_json = '''
        {
            "version": "0000000000000000000000000000000000000000",
            "schema_versions":
            [
                {
                    "schema_version": 1,
                    "content": "MQ=="
                }
            ]
        }
        '''

        content = service.DatabaseUpdateContent(content_json)

        assert content.version == '0000000000000000000000000000000000000000'
        self._assert_schema_version(content, 0, 1, b'1')

    def _assert_schema_version(self, update_content, index, schema_version,
                               content):
        content_schema_version = update_content.schema_versions[index]
        assert content_schema_version.schema_version == schema_version
        assert content_schema_version.content == content

    def test_multiple_schema_versions_succeed(self):
        content_json = '''
        {
            "version": "0000000000000000000000000000000000000000",
            "schema_versions":
            [
                {
                    "schema_version": 1,
                    "content": "MQ=="
                },
                {
                    "schema_version": 2,
                    "content": "Mg=="
                },
                {
                    "schema_version": 3,
                    "content": "Mw=="
                }
            ]
        }
        '''

        content = service.DatabaseUpdateContent(content_json)

        assert content.version == '0000000000000000000000000000000000000000'
        for i in range(1, 4):
            self._assert_schema_version(
                content, i - 1, i, self._int_to_bytes(i)
            )

    def _int_to_bytes(self, int_value):
        str_value = str(int_value)
        return str_value.encode('ascii')

    def test_invalid_json_fails(self):
        content_json = '{ "hello world": "hello world" }'

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Invalid content JSON' in str(ex_info)

    def test_null_version_fails(self):
        content_json = self._build_content(None, 1, 'MQ==')

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Version is not a string' in str(ex_info)

    def _build_content(self, version, schema_version, content):
        return json.dumps(dict(
            version=version,
            schema_versions=[
                dict(schema_version=schema_version, content=content)
            ]
        ))

    def test_all_valid_character_version_succeeds(self):
        version = '0123456789abcdef0123456789abcdef01234567'
        content_json = self._build_content(
            version, 1, 'MQ=='
        )
        content = service.DatabaseUpdateContent(content_json)

        assert content.version == version

    def test_empty_version_fails(self):
        content_json = self._build_content('', 1, 'MQ==')

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Version length is not 40 characters' in str(ex_info)

    def test_invalid_character_version_fails(self):
        content_json = self._build_content(
            '_000000000000000000000000000000000000000', 1, 'MQ=='
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Version contains invalid characters' in str(ex_info)

    def test_not_int_schema_version_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', '1', 'MQ=='
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Schema version is not an integer' in str(ex_info)

    def test_too_small_schema_version_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', 0, 'MQ=='
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Schema version does not fall into required' in str(ex_info)

    def test_too_big_schema_version_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', 2 ** 17, 'MQ=='
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Schema version does not fall into required' in str(ex_info)

    def test_non_unique_schema_versions_fails(self):
        content_json = json.dumps(dict(
            version='0000000000000000000000000000000000000000',
            schema_versions=[
                dict(schema_version=1, content='MQ=='),
                dict(schema_version=1, content='MQ=='),
                dict(schema_version=2, content='MQ==')
            ]
        ))

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Schema versions are not unique' in str(ex_info)

    def test_non_base64_content_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', 1, '1'
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Invalid content JSON' in str(ex_info)

    def test_null_content_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', 1, None
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Content is not a byte sequence' in str(ex_info)

    def test_empty_content_fails(self):
        content_json = self._build_content(
            '0000000000000000000000000000000000000000', 1, ''
        )

        with pytest.raises(service.InvalidUpdateContentError) as ex_info:
            service.DatabaseUpdateContent(content_json)
        assert 'Content is empty' in str(ex_info)


class TestApplyUpdate(BaseDbAwareTest):
    HASH_SIZE = 40
    ASCII_ENCODING = 'ascii'

    def test_empty_db_update_succeeds(self):
        self.init_database([])

        content_dict = dict(
            version=self._make_version(1),
            schema_versions=[
                dict(
                    schema_version=1,
                    content=self._make_base64_content(1)
                ),
                dict(
                    schema_version=2,
                    content=self._make_base64_content(2)
                ),
            ]
        )
        self._apply_update(content_dict)

        expected_databases = [
            db.Database(
                version=self._make_version(1),
                schema_version=1,
                content=self._make_content(1)
            ),
            db.Database(
                version=self._make_version(1),
                schema_version=2,
                content=self._make_content(2)
            ),
        ]

        self._assert_databases(expected_databases)

    def _make_version(self, index):
        # 1..9 is enough for testing
        assert 1 <= index <= 9
        return str(index) * self.HASH_SIZE

    def _make_base64_content(self, index):
        content = self._make_content(index)
        return service.Base64.binary_to_base64_str(content)

    def _make_content(self, index):
        return str(index).encode()

    def _apply_update(self, content_dict):
        content_json = json.dumps(content_dict)
        update_content = service.DatabaseUpdateContent(content_json)
        service.DatabaseUpdate().apply_update(update_content)

    def _assert_databases(self, expected_databases):
        with db.Session() as session:
            stored_databases = session.query(db.Database).all()

            assert len(stored_databases) == len(expected_databases)
            for expected_database in expected_databases:
                assert self._database_exists(
                    stored_databases, expected_database
                )

    def _database_exists(self, stored_databases, expected_database):
        stored_database = next(
            (x for x in stored_databases
             if self._database_equals(x, expected_database)),
            None
        )

        return stored_database is not None

    def _database_equals(self, stored, expected):
        return (
            stored.version == expected.version and
            stored.schema_version == expected.schema_version and
            stored.content == expected.content
        )

    def test_non_intersecting_db_update_succeeds(self):
        existing_databases = [
            db.Database(
                version=self._make_version(1),
                schema_version=1,
                content=self._make_content(1)
            ),
            db.Database(
                version=self._make_version(2),
                schema_version=2,
                content=self._make_content(2)
            )
        ]
        self.init_database(existing_databases)

        content_dict = dict(
            version=self._make_version(3),
            schema_versions=[
                dict(
                    schema_version=3,
                    content=self._make_base64_content(3)
                ),
                dict(
                    schema_version=4,
                    content=self._make_base64_content(4)
                ),
            ]
        )
        self._apply_update(content_dict)

        expected_databases = [
            db.Database(
                version=self._make_version(1),
                schema_version=1,
                content=self._make_content(1)
            ),
            db.Database(
                version=self._make_version(2),
                schema_version=2,
                content=self._make_content(2)
            ),
            db.Database(
                version=self._make_version(3),
                schema_version=3,
                content=self._make_content(3)
            ),
            db.Database(
                version=self._make_version(3),
                schema_version=4,
                content=self._make_content(4)
            ),
        ]

        self._assert_databases(expected_databases)

    def test_intersecting_db_update_succeeds(self):
        existing_databases = [
            db.Database(
                version=self._make_version(1),
                schema_version=1,
                content=self._make_content(1)
            ),
            db.Database(
                version=self._make_version(2),
                schema_version=2,
                content=self._make_content(2)
            )
        ]
        self.init_database(existing_databases)

        content_dict = dict(
            version=self._make_version(3),
            schema_versions=[
                dict(
                    schema_version=2,
                    content=self._make_base64_content(4)
                ),
                dict(
                    schema_version=3,
                    content=self._make_base64_content(6)
                ),
            ]
        )
        self._apply_update(content_dict)

        expected_databases = [
            db.Database(
                version=self._make_version(1),
                schema_version=1,
                content=self._make_content(1)
            ),
            db.Database(
                version=self._make_version(3),
                schema_version=2,
                content=self._make_content(4)
            ),
            db.Database(
                version=self._make_version(3),
                schema_version=3,
                content=self._make_content(6)
            )
        ]

        self._assert_databases(expected_databases)


KeyPair = collections.namedtuple('KeyPair', 'private, public')


class PublicKeySshCodec:
    BITS_PER_UINT = 32
    BITS_PER_BYTE = 8
    SSH_RSA_HEADER = b'ssh-rsa'

    def encode(self, public_key):
        public_numbers = public_key.public_numbers()

        sections = [
            self.SSH_RSA_HEADER,
            self._multi_precision_int_to_bytes(public_numbers.e),
            self._multi_precision_int_to_bytes(public_numbers.n)
        ]

        binary_keystring = b''.join(
            [self._get_len_prefix(x) + x for x in sections]
        )

        return self.SSH_RSA_HEADER + b' ' + base64.b64encode(binary_keystring)

    def _multi_precision_int_to_bytes(self, int_value):
        sequence = self._int_to_bytes(int_value, int_value.bit_length())

        # If the leftmost bit of the first byte is 1 than it means encoded
        # integer is negative. When leftmost bit of the first byte happens
        # to be set for a positive integer, a zero byte should be prepended
        # to the sequence.
        #
        # See section Data Type Representations Used in the SSH Protocols
        # in RFC 4251 for more information
        first_bit_char = 0b1000000
        zero_char = 0b00000000
        if sequence[0] & first_bit_char:
            sequence = (
                self._int_to_bytes(zero_char, self.BITS_PER_UINT) + sequence
            )

        return sequence

    def _int_to_bytes(self, int_value, bit_len):
        if not bit_len:
            bit_len = int_value.bit_length()

        mod = bit_len % self.BITS_PER_BYTE
        if mod > 0:
            bit_len += self.BITS_PER_BYTE - mod

        byte_len = int(bit_len / self.BITS_PER_BYTE)
        return int_value.to_bytes(byte_len, byteorder='big')

    def _get_len_prefix(self, byte_sequence):
        return self._int_to_bytes(len(byte_sequence), self.BITS_PER_UINT)


class TestSignatureVerifier:
    UTF8_ENCODING = 'utf-8'
    PUBLIC_EXPONENT = 65537
    KEY_SIZE = 2048

    def test_predefined_signature(self):
        # Externally (via Java) precalculated signature and corresponding
        # public key binary in OpenSSH format
        signature = (
            b'\x46\xfc\x45\x23\x9f\x52\x76\xeb\xca\xf8\xf4\xbc\x0c\xb7\xf3\xa1'
            b'\xfa\xe2\xc2\xe9\xb6\xe2\x4c\x77\x12\xd6\x37\xe6\xb1\x35\xd4\x2a'
            b'\xa5\x14\x2d\xe8\x1b\x13\xe9\xcd\x26\x6a\xed\x52\xfa\xee\x13\xc4'
            b'\x32\x80\x9f\xa4\xa5\xe8\x56\x16\x73\x2d\x7f\x82\x50\xc2\xdf\x08'
            b'\xd0\x5b\xea\xbc\xe2\xfe\x61\xb2\xe4\x7c\x5b\x75\xe4\x87\xd9\xf8'
            b'\xa3\xfd\x99\xd2\xeb\x41\xa2\xd4\x0d\xbe\xfa\xd1\x32\xcd\x25\x2f'
            b'\xd0\x97\x64\xc4\x9b\xa6\x00\x51\x69\x81\x05\x60\xad\xfe\x8d\x4b'
            b'\x2e\xf8\x5e\xa9\x65\x5f\xb7\x38\x76\xba\xf7\xbc\x6b\xa9\x1c\xb7'
        )
        public_key_binary = (
            b'\x73\x73\x68\x2d\x72\x73\x61\x20\x41\x41\x41\x41\x42\x33\x4e\x7a'
            b'\x61\x43\x31\x79\x63\x32\x45\x41\x41\x41\x41\x44\x41\x51\x41\x42'
            b'\x41\x41\x41\x41\x67\x51\x43\x61\x72\x55\x65\x5a\x69\x6f\x72\x6f'
            b'\x33\x53\x78\x47\x70\x77\x59\x2f\x45\x75\x2b\x55\x2b\x33\x53\x68'
            b'\x31\x31\x39\x39\x64\x4b\x49\x49\x36\x54\x61\x51\x78\x73\x32\x64'
            b'\x61\x54\x67\x34\x39\x6b\x76\x58\x39\x73\x53\x57\x73\x50\x5a\x76'
            b'\x73\x74\x4d\x50\x35\x36\x2f\x64\x6b\x70\x5a\x53\x30\x2f\x7a\x30'
            b'\x4c\x76\x53\x68\x73\x69\x38\x53\x51\x38\x2b\x35\x66\x58\x32\x6c'
            b'\x78\x45\x53\x6f\x78\x5a\x72\x6a\x74\x4b\x77\x35\x34\x34\x36\x6e'
            b'\x6c\x78\x4f\x54\x73\x2b\x46\x58\x6c\x4e\x35\x39\x45\x43\x5a\x37'
            b'\x6c\x51\x4c\x50\x46\x4a\x7a\x4b\x76\x46\x47\x4f\x62\x65\x46\x6a'
            b'\x36\x4f\x38\x5a\x41\x55\x47\x77\x73\x63\x6a\x38\x64\x42\x65\x49'
            b'\x79\x36\x79\x63\x63\x64\x53\x4a\x63\x46\x66\x35\x32\x35\x4c\x31'
            b'\x73\x77\x3d\x3d'
        )
        text = 'Hello world'

        assert service.SignatureVerifier().verify(
            [public_key_binary], text, signature
        )

    def test_single_key_succeeds(self):
        key = self._make_key_pair()
        text = 'lorem ipsum'

        signature = self._sign_text(text, key.private)

        assert service.SignatureVerifier().verify(
            [key.public], text, signature
        )

    def _make_key_pair(self):
        private_key = crypto_rsa.generate_private_key(
            self.PUBLIC_EXPONENT, self.KEY_SIZE, crypto_backend()
        )

        private_key_binary = private_key.private_bytes(
            encoding=crypto_serial.Encoding.PEM,
            format=crypto_serial.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=crypto_serial.NoEncryption()
        )
        public_key_binary = PublicKeySshCodec().encode(
            private_key.public_key()
        )

        pair = KeyPair(
            private=private_key_binary,
            public=public_key_binary
        )

        return pair

    def _sign_text(self, text, private_key_binary):
        private_key = crypto_serial.load_pem_private_key(
            private_key_binary, password=None, backend=crypto_backend()
        )
        signer = private_key.signer(
            crypto_padding.PKCS1v15(), crypto_hashes.SHA512()
        )

        signer.update(text.encode(self.UTF8_ENCODING))

        return signer.finalize()

    def test_multiple_keys_succeeds(self):
        valid_key = self._make_key_pair()
        text = 'lorem ipsum'

        signature = self._sign_text(text, valid_key.private)

        keys = [
            self._make_key_pair().public,
            valid_key.public,
            self._make_key_pair().public
        ]
        assert service.SignatureVerifier().verify(
            keys, text, signature
        )

    def test_invalid_keys_fails(self):
        text = 'lorem ipsum'

        signature = self._sign_text(text, self._make_key_pair().private)

        keys = [
            self._make_key_pair().public,
            self._make_key_pair().public,
            self._make_key_pair().public
        ]
        assert not service.SignatureVerifier().verify(
            keys, text, signature
        )


class TestSha256:
    def test(self):
        digest = service.Sha256().make_hash(b'lorem ipsum')
        expected = ('5e2bf57d3f40c4b6df69daf1936cb766f832374b4fc0259a7cbff06e2'
                    'f70f269')
        assert digest == expected

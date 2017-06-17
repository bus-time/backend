# coding: utf-8


import os
import tempfile

from cryptography.hazmat.backends import default_backend as crypto_backend
from cryptography.hazmat.primitives import serialization as crypto_serial

from backend import config


class TestEnvVariableKeyBinarySource:
    ASCII_ENCODING = 'ascii'

    def test_existant_succeeds(self):
        env_dict = {
            'lorem': '1',
            'BUSTIME_PUBLICATION_KEY_FIRST': 'first',
            'ipsum': '2',
            'BUSTIME_PUBLICATION_KEY_SECOND': 'second',
            'dolor': '3'
        }

        keys = config.EnvVariableKeyBinarySource(env_dict).get_key_binaries()

        assert set(keys) == { b'first', b'second' }

    def test_non_existant_yields_empty(self):
        env_dict = {
            'lorem': 'ipsum',
            'dolor': 'sit'
        }

        keys = config.EnvVariableKeyBinarySource(env_dict).get_key_binaries()

        assert set(keys) == set()

    def test_key_imports(self):
        ssh_generated_public_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCxoUay/ABidJgol/uA3meDOtPL4g4RR5Q7Qx40YPUgVQErk/khTher9QpS0qAuczwG6Ck7YwRHRW5MLSV+6IaXZWjZKU98kWUUNWzdxm+s5PLWUyDScotilwRW2EibPjBSjip4fEjMa5bMB8ZrC36cSvHMZ3y93OEu3pIl8Z45Cu/mDIu0KodYkoQTr9dXCmTfP8sDx18WtZ0j4DAafjdhVtiystqFYBAFLrWX1QDaFbX9HMyna9rDiL2RTCSIcpSzO6LRrhacCCN4w+Ej0Vv0YxG0nk93w3DHRuPOWygNJVFnDgXtnwkx+LkJvqaemcrD+/7rVHjLYusSlG1/6BJz example@example.com'

        env_dict = {
            'BUSTIME_PUBLICATION_KEY_FIRST': ssh_generated_public_key
        }

        keys = config.EnvVariableKeyBinarySource(env_dict).get_key_binaries()

        assert len(keys) == 1

        key = keys[0]
        assert key == ssh_generated_public_key.encode(self.ASCII_ENCODING)

        key_object = crypto_serial.load_ssh_public_key(key, crypto_backend())
        assert key_object is not None


class TestDirectoryKeyBinarySource:
    WRITE_BINARY_MODE = 'wb'

    def test_succeeds(self):
        with tempfile.TemporaryDirectory() as dir_name:
            self._write_file(dir_name, 'first.pub', b'first')
            self._write_file(dir_name, 'second.pub', b'second')
            self._write_file(dir_name, 'third.txt', b'third')

            keys = config.DirectoryKeyBinarySource(dir_name).get_key_binaries()
            assert set(keys) == { b'first', b'second' }

    def _write_file(self, dir_name, file_name, content):
        full_file_name = os.path.join(dir_name, file_name)

        with open(full_file_name, mode=self.WRITE_BINARY_MODE) as f:
            f.write(content)

    def test_invalid_dir_yields_empty_key_sequence(self):
        invalid_dir = '~/~'
        keys = config.DirectoryKeyBinarySource(invalid_dir).get_key_binaries()
        assert len(keys) == 0

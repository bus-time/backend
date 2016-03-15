# coding: utf-8


import abc
import collections
import configparser
import os


class Config(metaclass=abc.ABCMeta):
    HEROKU_DYNO_VARIABLE = 'DYNO'
    OPENSHIFT_APP_NAME_VARIABLE = 'OPENSHIFT_APP_NAME'

    _config = None

    @property
    @abc.abstractmethod
    def db_url(self):
        pass

    @property
    @abc.abstractmethod
    def key_binaries(self):
        pass

    @classmethod
    def get(cls):
        return cls._config

    @classmethod
    def init(cls, config=None):
        cls._config = config or cls._create()

    @classmethod
    def _create(cls):
        if cls._is_heroku_hosted():
            return HerokuConfig()
        elif cls._is_openshift_hosted():
            return OpenShiftConfig()
        else:
            return FileConfig()

    @classmethod
    def _is_heroku_hosted(cls):
        return cls.HEROKU_DYNO_VARIABLE in os.environ

    @classmethod
    def _is_openshift_hosted(cls):
        return cls.OPENSHIFT_APP_NAME_VARIABLE in os.environ

    def _get_script_dir(self):
        return os.path.dirname(os.path.realpath(__file__))


class HerokuConfig(Config):
    ENV_DATABASE_URL = 'DATABASE_URL'
    KEY_DIR = '../config'

    @property
    def db_url(self):
        return os.environ[self.ENV_DATABASE_URL]

    @property
    def key_binaries(self):
        return EnvVariableKeyBinarySource(os.environ).get_key_binaries()


class OpenShiftConfig(Config):
    DATABASE_URL_TEMPLATE = 'postgresql://{}:{}'
    ENV_DATABASE_HOST = 'OPENSHIFT_POSTGRESQL_DB_HOST'
    ENV_DATABASE_PORT = 'OPENSHIFT_POSTGRESQL_DB_PORT'

    KEY_DIR = '../config'

    @property
    def db_url(self):
        return self.DATABASE_URL_TEMPLATE.format(
            os.environ.get(self.ENV_DATABASE_HOST),
            os.environ.get(self.ENV_DATABASE_PORT)
        )

    @property
    def key_binaries(self):
        return EnvVariableKeyBinarySource(os.environ).get_key_binaries()


class FileConfig(Config):
    ConfigKey = collections.namedtuple('ConfigKey', ['section', 'option'])

    CONFIG_FILE_DIR = '../config'
    CONFIG_FILE_NAME = 'backend.ini'
    PUBLIC_KEY_DIR = '~/.ssh'

    DB_URL_CONFIG_KEY = ConfigKey('db', 'url')

    def __init__(self):
        self._config_parser = self._get_config_parser()

    def _get_config_parser(self):
        parser = configparser.ConfigParser()
        parser.read(self._get_config_file_path())
        return parser

    def _get_config_file_path(self):
        return os.path.join(self._get_config_dir_path(), self.CONFIG_FILE_NAME)

    def _get_config_dir_path(self):
        relative = os.path.join(self._get_script_dir(), self.CONFIG_FILE_DIR)
        return os.path.abspath(relative)

    @property
    def db_url(self):
        return self._config_parser.get(
            self.DB_URL_CONFIG_KEY.section,
            self.DB_URL_CONFIG_KEY.option
        )

    @property
    def key_binaries(self):
        return DirectoryKeyBinarySource(self.PUBLIC_KEY_DIR).get_key_binaries()


class KeyBinarySource(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_key_binaries(self):
        pass


class EnvVariableKeyBinarySource(KeyBinarySource):
    PREFIX = 'BUSTIME_PUBLICATION_KEY_'
    ASCII_ENCODING = 'ascii'

    def __init__(self, env_variable_dict):
        self._env_variable_dict = env_variable_dict

    def get_key_binaries(self):
        return [
            v.encode(self.ASCII_ENCODING)
            for k, v in self._env_variable_dict.items()
            if k.startswith(self.PREFIX)
        ]


class DirectoryKeyBinarySource(KeyBinarySource):
    KEY_POSTFIX = '.pub'
    READ_BINARY_MODE = 'rb'

    def __init__(self, directory):
        self._directory = directory

    def get_key_binaries(self):
        return [
            self._read_file(self._directory, x)
            for x in os.listdir(self._directory)
            if x.endswith(self.KEY_POSTFIX)
        ]

    def _read_file(self, dir_name, file_name):
        full_file_name = os.path.join(dir_name, file_name)
        with open(full_file_name, mode=self.READ_BINARY_MODE) as f:
            return f.read()



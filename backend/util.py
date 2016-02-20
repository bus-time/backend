# coding: utf-8


import abc
import configparser
import collections
import os


class Config(metaclass=abc.ABCMeta):
    _config = None

    HEROKU_DYNO_VARIABLE = 'DYNO'
    OPENSHIFT_APP_NAME_VARIABLE = 'OPENSHIFT_APP_NAME'

    @property
    @abc.abstractmethod
    def db_url(self):
        pass

    @property
    @abc.abstractmethod
    def deployment_key_dir(self):
        pass

    @classmethod
    def get(cls):
        if not cls._config:
            cls._config = cls._create()
        return cls._config

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
    def deployment_key_dir(self):
        relative = os.path.join(self._get_script_dir(), self.KEY_DIR)
        return os.path.abspath(relative)


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
    def deployment_key_dir(self):
        relative = os.path.join(self._get_script_dir(), self.KEY_DIR)
        return os.path.abspath(relative)


class FileConfig(Config):
    ConfigKey = collections.namedtuple('ConfigKey', ['section', 'option'])

    CONFIG_FILE_DIR = '../config'
    CONFIG_FILE_NAME = 'backend.ini'

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
    def deployment_key_dir(self):
        return self._get_config_dir_path()

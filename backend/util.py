# coding: utf-8


import configparser
import collections
import os


class Config(object):
    ConfigKey = collections.namedtuple('ConfigKey', ['section', 'option'])

    CONFIG_FILE_DIR = '../config'
    CONFIG_FILE_NAME = 'backend.ini'

    VALUE_DB_URL = ConfigKey('db', 'url')

    ENV_HEROKU_DATABASE_URL = 'DATABASE_URL'

    OPENSHIFT_POSTGRESQL_URL_TEMPLATE = 'postgresql://{}:{}'
    ENV_OPENSHIFT_POSTGRESQL_DB_HOST = 'OPENSHIFT_POSTGRESQL_DB_HOST'
    ENV_OPENSHIFT_POSTGRESQL_DB_PORT = 'OPENSHIFT_POSTGRESQL_DB_PORT'

    @classmethod
    def get_config_value(cls, config_key):
        parser = cls.get_config_parser()

        if not parser.has_section(config_key.section):
            parser.add_section(config_key.section)

        return parser.get(config_key.section, config_key.option)

    @classmethod
    def get_config_parser(cls):
        parser = configparser.ConfigParser(defaults=cls.get_defaults())
        parser.read(cls.get_config_file_path())
        return parser

    @classmethod
    def get_defaults(cls):
        if cls.is_heroku_hosted():
            return cls.get_heroku_defaults()
        elif cls.is_openshift_hosted():
            return cls.get_openshift_defaults()
        else:
            return None

    @classmethod
    def is_heroku_hosted(cls):
        return os.environ.get(cls.ENV_HEROKU_DATABASE_URL) is not None

    @classmethod
    def get_heroku_defaults(cls):
        return {
            cls.VALUE_DB_URL.option: os.environ[cls.ENV_HEROKU_DATABASE_URL],
        }

    @classmethod
    def is_openshift_hosted(cls):
        return os.environ.get(cls.ENV_OPENSHIFT_POSTGRESQL_DB_HOST) is not None

    @classmethod
    def get_openshift_defaults(cls):
        return {
            cls.VALUE_DB_URL.option: cls.get_openshift_db_url()
        }

    @classmethod
    def get_openshift_db_url(cls):
        return cls.OPENSHIFT_POSTGRESQL_URL_TEMPLATE.format(
            os.environ.get(cls.ENV_OPENSHIFT_POSTGRESQL_DB_HOST),
            os.environ.get(cls.ENV_OPENSHIFT_POSTGRESQL_DB_PORT)
        )

    @classmethod
    def get_config_file_path(cls):
        return os.path.join(cls.get_config_dir_path(), cls.CONFIG_FILE_NAME)

    @classmethod
    def get_config_dir_path(cls):
        relative_path = os.path.join(cls.get_script_dir(), cls.CONFIG_FILE_DIR)
        return os.path.abspath(relative_path)

    @classmethod
    def get_script_dir(cls):
        return os.path.dirname(os.path.realpath(__file__))

    @classmethod
    def get_deployment_key_dir(cls):
        return cls.get_config_dir_path()

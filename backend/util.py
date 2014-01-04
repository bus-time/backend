# coding: utf-8


from __future__ import absolute_import, unicode_literals
import os
import ConfigParser
import collections


class Config(object):
    ConfigKey = collections.namedtuple('ConfigKey', ['section', 'option'])

    CONFIG_FILE_DIR = '../config'
    CONFIG_FILE_NAME = 'backend.ini'

    VALUE_DB_URL = ConfigKey('db', 'url')

    ENV_HEROKU_DATABASE_URL = 'DATABASE_URL'
    HEROKU_TMP_DIR = '/tmp'

    @classmethod
    def get_config_value(cls, config_key):
        parser = cls.get_config_parser()
        if not parser.has_section(config_key.section):
            parser.add_section(config_key.section)

        return parser.get(config_key.section, config_key.option)

    @classmethod
    def get_config_parser(cls):
        parser = ConfigParser.SafeConfigParser(defaults=cls.get_defaults())
        parser.read(cls.get_config_file_path())
        return parser

    @classmethod
    def get_defaults(cls):
        if cls.is_heroku_hosted():
            return cls.get_heroku_defaults()
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

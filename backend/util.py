# coding: utf-8


from __future__ import absolute_import, unicode_literals
import os
import ConfigParser


class Config(object):
    CONFIG_FILE_NAME = 'backend.ini'
    CONFIG_SECTION_NAME = 'general'

    VALUE_DB_URL = 'db-url'
    VALUE_DB_REPO_DOWNLOAD_DIR = 'db-repo-download-dir'

    ENV_HEROKU_DATABASE_URL = 'DATABASE_URL'
    HEROKU_TMP_DIR = '/tmp'

    DEPLOYMENT_KEY_DIR = 'deployment-keys'

    @classmethod
    def get_config_value(cls, value_name):
        return cls.get_config_parser().get(cls.CONFIG_SECTION_NAME, value_name)

    @classmethod
    def get_config_parser(cls):
        config = ConfigParser.SafeConfigParser(defaults=cls.get_defaults())
        config.read(cls.get_config_file_path())
        if not config.has_section(cls.CONFIG_SECTION_NAME):
            config.add_section(cls.CONFIG_SECTION_NAME)
        return config

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
            cls.VALUE_DB_URL: os.environ[cls.ENV_HEROKU_DATABASE_URL],
            cls.VALUE_DB_REPO_DOWNLOAD_DIR: cls.HEROKU_TMP_DIR
        }

    @classmethod
    def get_config_file_path(cls):
        dir = os.path.abspath(os.path.join(cls.get_script_dir(), '..'))
        return os.path.join(dir, cls.CONFIG_FILE_NAME)

    @classmethod
    def get_script_dir(cls):
        return os.path.dirname(os.path.realpath(__file__))

    @classmethod
    def get_deployment_key_dir(cls):
        return os.path.join(cls.get_script_dir(), cls.DEPLOYMENT_KEY_DIR)

# coding: utf-8


from __future__ import absolute_import, unicode_literals
import os
import ConfigParser


class Config(object):
    CONFIG_FILE_NAME = 'backend.ini'
    CONFIG_SECTION_NAME = 'general'

    VALUE_DB_URL = 'db-url'
    VALUE_DB_REPO_DOWNLOAD_DIR = 'db-repo-download-dir'

    ENV_OPENSHIFT_HOME_DIR = 'OPENSHIFT_HOMEDIR'
    ENV_OPENSHIFT_DB_URL = 'OPENSHIFT_POSTGRESQL_DB_URL'
    ENV_OPENSHIFT_DATA_DIR = 'OPENSHIFT_DATA_DIR'

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
        if cls.is_openshift_hosted():
            return cls.get_openshift_defaults()
        else:
            return None

    @classmethod
    def is_openshift_hosted(cls):
        return os.environ.get(cls.ENV_OPENSHIFT_HOME_DIR) is not None

    @classmethod
    def get_openshift_defaults(cls):
        return {
            cls.VALUE_DB_URL: os.environ[cls.ENV_OPENSHIFT_DB_URL],
            cls.VALUE_DB_REPO_DOWNLOAD_DIR: os.environ[
                cls.ENV_OPENSHIFT_DATA_DIR]
        }

    @classmethod
    def get_config_file_path(cls):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dir = os.path.abspath(os.path.join(script_dir, '..'))
        return os.path.join(dir, cls.CONFIG_FILE_NAME)

# coding: utf-8


from __future__ import absolute_import, unicode_literals
import os
import ConfigParser


class Config(object):
    CONFIG_FILE_NAME = 'backend.ini'
    CONFIG_SECTION_NAME = 'general'

    VALUE_DB_URL = 'db-url'
    VALUE_DB_REPO_DOWNLOAD_DIR = 'db-repo-download-dir'

    @classmethod
    def get_config_file_path(cls):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        dir = os.path.abspath(os.path.join(script_dir, '..'))
        return os.path.join(dir, cls.CONFIG_FILE_NAME)

    @classmethod
    def get_config_parser(cls):
        config = ConfigParser.SafeConfigParser()
        config.read(cls.get_config_file_path())
        return config

    @classmethod
    def get_config_value(cls, value_name):
        return cls.get_config_parser().get(cls.CONFIG_SECTION_NAME, value_name)

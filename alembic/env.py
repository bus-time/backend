# coding: utf-8


from __future__ import absolute_import, unicode_literals
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
import sys


config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)


def get_backend_root():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(script_dir, '..'))


def setup_pythonpath():
    sys.path.append(get_backend_root())


def get_target_metadata():
    setup_pythonpath()
    from backend.db import Base
    return Base.metadata


# Add model's MetaData object for 'autogenerate' support
target_metadata = get_target_metadata()


def get_db_url():
    setup_pythonpath()
    from backend.util import Config as BackendConfig
    BackendConfig.init()
    return BackendConfig.get().db_url


def run_migrations_offline():
    context.configure(url=get_db_url())

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    alembic_config = config.get_section(config.config_ini_section)
    alembic_config['sqlalchemy.url'] = get_db_url()

    engine = engine_from_config(
        alembic_config,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


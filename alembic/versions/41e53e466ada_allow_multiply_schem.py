# coding: utf-8


"""Allow multiply schema version of same version.

Revision ID: 41e53e466ada
Revises: 56d86c6ed4b4
Create Date: 2014-02-08 22:56:27.170739

"""


from __future__ import absolute_import


revision = '41e53e466ada'
down_revision = '56d86c6ed4b4'


import sqlalchemy as sa
from alembic import op


def upgrade():
    op.drop_constraint('databases_schema_version_key', 'databases')
    op.drop_constraint('databases_version_key', 'databases')

    op.create_unique_constraint('databases_schema_version_version_key',
                                'databases',
                                ['schema_version', 'version'])


def downgrade():
    op.drop_constraint('databases_schema_version_version_key', 'databases')

    op.create_unique_constraint('databases_schema_version_key',
                                'databases',
                                ['schema_version'])
    op.create_unique_constraint('databases_version_key',
                                'databases',
                                ['version'])

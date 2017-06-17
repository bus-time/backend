# coding: utf-8


"""unique schema version

Revision ID: 3a54b8cfb6eb
Revises: 41e53e466ada
Create Date: 2016-03-15 19:49:40.721733

"""


from __future__ import absolute_import


revision = '3a54b8cfb6eb'
down_revision = '41e53e466ada'


import sqlalchemy as sa
from alembic import op

def upgrade():
    op.drop_constraint('databases_schema_version_version_key', 'databases')

    op.create_unique_constraint('databases_schema_version_key',
                                'databases',
                                ['schema_version'])

def downgrade():
    op.drop_constraint('databases_schema_version_key', 'databases')

    op.create_unique_constraint('databases_schema_version_version_key',
                                'databases',
                                ['schema_version', 'version'])


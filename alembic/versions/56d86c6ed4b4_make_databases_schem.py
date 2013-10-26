# coding: utf-8


"""Make databases.schema_version of an integer type.

Revision ID: 56d86c6ed4b4
Revises: 1be77c5b8092
Create Date: 2013-10-26 20:49:14.806816

"""


from __future__ import absolute_import


revision = '56d86c6ed4b4'
down_revision = '1be77c5b8092'


import sqlalchemy as sa
from alembic import op


def upgrade():
    op.drop_table(u'databases')
    op.create_table(u'databases',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('schema_version', sa.Integer(), nullable=False),
                    sa.Column('version', sa.String(), nullable=False),
                    sa.Column('contents', sa.Binary(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('schema_version'),
                    sa.UniqueConstraint('version'))


def downgrade():
    op.drop_table(u'databases')
    op.create_table(u'databases',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('schema_version', sa.String(), nullable=False),
                    sa.Column('version', sa.String(), nullable=False),
                    sa.Column('contents', sa.Binary(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('schema_version'),
                    sa.UniqueConstraint('version'))

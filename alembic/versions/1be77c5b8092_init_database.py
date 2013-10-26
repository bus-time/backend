# coding: utf-8


"""Init database.

Revision ID: 1be77c5b8092
Revises: None
Create Date: 2013-10-26 20:36:47.786532

"""


from __future__ import absolute_import


revision = '1be77c5b8092'
down_revision = None


import sqlalchemy as sa
from alembic import op


def upgrade():
    op.create_table(u'databases',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('schema_version', sa.String(), nullable=False),
                    sa.Column('version', sa.String(), nullable=False),
                    sa.Column('contents', sa.Binary(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('schema_version'),
                    sa.UniqueConstraint('version'))


def downgrade():
    op.drop_table(u'databases')

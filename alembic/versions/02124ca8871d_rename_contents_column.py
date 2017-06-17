# coding: utf-8


"""rename contents column

Revision ID: 02124ca8871d
Revises: 3a54b8cfb6eb
Create Date: 2016-03-15 20:05:54.005547

"""


from __future__ import absolute_import


revision = '02124ca8871d'
down_revision = '3a54b8cfb6eb'


import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('databases', 'contents', new_column_name='content')


def downgrade():
    op.alter_column('databases', 'content', new_column_name='contents')

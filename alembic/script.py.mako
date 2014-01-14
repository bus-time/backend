\
# coding: utf-8


"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""


from __future__ import absolute_import


revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}


import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}

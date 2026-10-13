from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine

import irerero_contract.tables  # noqa: F401  (registers every table on the metadata)
from irerero_api.config import get_settings
from irerero_contract.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            include_object=alembic_helpers.include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()

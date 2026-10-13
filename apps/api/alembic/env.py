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


def include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """Compare only contract tables. PostGIS images ship extra schemas (tiger, topology)."""
    table = obj if type_ == "table" else getattr(obj, "table", None)
    table_name = getattr(table, "name", None)
    if reflected and table_name is not None and table_name not in Base.metadata.tables:
        return False
    return bool(alembic_helpers.include_object(obj, name, type_, reflected, compare_to))


def run_migrations() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()

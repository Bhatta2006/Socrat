import os

from alembic import context
from sqlalchemy import create_engine, pool

from socrat.config import DatabaseSettings
from socrat.models import Base

config = context.config
database_environment_present = any(name.startswith("SOCRAT_DATABASE_") for name in os.environ)
settings = (
    DatabaseSettings()
    if database_environment_present
    else DatabaseSettings(database_url=config.get_main_option("sqlalchemy.url"))
)
url = settings.database_url_value
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

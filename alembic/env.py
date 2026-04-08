"""Alembic environment configuration."""
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool


# Alembic Config object
config = fileConfig(os.path.join(os.path.dirname(__file__), '..', 'alembic.ini'))

# This is the Alembic Config object, which provides
# the values of the [alembic] section of the alembic.ini
# file as Python variables within this module.
from alembic import context

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///./data/tailsentry.db"
    )
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

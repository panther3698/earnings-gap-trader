"""
Database configuration and initialization for Earnings Gap Trader
"""
import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, MetaData, event, exc, pool, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

import config
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


class DatabaseManager:
    """Database manager with connection pooling and error handling"""
    
    def __init__(self, database_url: str = None, debug: bool = None):
        self.database_url = database_url or config.DATABASE_URL
        self.debug = debug if debug is not None else config.DEBUG
        self._engine = None
        self._session_factory = None
        
    @property
    def engine(self):
        """Get database engine with lazy initialization"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def session_factory(self):
        """Get session factory with lazy initialization"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._session_factory
    
    def _create_engine(self):
        """Create database engine with proper configuration"""
        connect_args = {}
        poolclass = None
        pool_kwargs = {}
        
        if "sqlite" in self.database_url:
            # SQLite specific settings
            connect_args = {
                "check_same_thread": False,
                "timeout": 30
            }
            poolclass = StaticPool
            pool_kwargs = {
                "pool_pre_ping": True,
                "pool_recycle": 300
            }
        else:
            # PostgreSQL/MySQL specific settings
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "pool_pre_ping": True
            }
        
        engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            poolclass=poolclass,
            echo=self.debug,
            **pool_kwargs
        )
        
        # Add event listeners for connection management
        self._add_engine_events(engine)
        
        return engine
    
    def _add_engine_events(self, engine):
        """Add event listeners for database connection management"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and reliability"""
            if "sqlite" in self.database_url:
                cursor = dbapi_connection.cursor()
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Set WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                # Set synchronous mode for better performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Set temp store to memory
                cursor.execute("PRAGMA temp_store=memory")
                # Set cache size
                cursor.execute("PRAGMA cache_size=10000")
                cursor.close()
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log database connection checkout"""
            logger.debug("Database connection checked out")
        
        @event.listens_for(engine, "checkin")  
        def receive_checkin(dbapi_connection, connection_record):
            """Log database connection checkin"""
            logger.debug("Database connection checked in")
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Context manager for database sessions with automatic cleanup"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Import all models to ensure they are registered
            from models import trade_models, config_models
            
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def get_table_info(self) -> dict:
        """Get information about database tables"""
        try:
            from sqlalchemy import inspect
            
            inspector = inspect(self.engine)
            table_info = {}
            
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                indexes = inspector.get_indexes(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                
                table_info[table_name] = {
                    'columns': len(columns),
                    'indexes': len(indexes),
                    'foreign_keys': len(foreign_keys)
                }
            
            return table_info
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}


class MigrationManager:
    """Alembic migration manager"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or config.DATABASE_URL
        self.alembic_cfg = None
        self._setup_alembic()
    
    def _setup_alembic(self):
        """Setup Alembic configuration"""
        try:
            # Create alembic directory if it doesn't exist
            alembic_dir = "alembic"
            if not os.path.exists(alembic_dir):
                os.makedirs(alembic_dir)
                os.makedirs(os.path.join(alembic_dir, "versions"))
            
            # Create alembic.ini if it doesn't exist
            alembic_ini = "alembic.ini"
            if not os.path.exists(alembic_ini):
                self._create_alembic_ini()
            
            self.alembic_cfg = Config(alembic_ini)
            self.alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
        except Exception as e:
            logger.error(f"Failed to setup Alembic: {e}")
    
    def _create_alembic_ini(self):
        """Create basic alembic.ini file"""
        alembic_ini_content = """# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = alembic

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version path separator; as mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = sqlite:///./earnings_gap_trader.db


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
        
        with open("alembic.ini", "w") as f:
            f.write(alembic_ini_content)
    
    def init_alembic(self):
        """Initialize Alembic migration environment"""
        try:
            if not os.path.exists("alembic/env.py"):
                command.init(self.alembic_cfg, "alembic")
            logger.info("Alembic initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Alembic: {e}")
            raise
    
    def create_migration(self, message: str):
        """Create a new migration"""
        try:
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            logger.info(f"Migration created: {message}")
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise
    
    def upgrade_database(self, revision: str = "head"):
        """Upgrade database to specified revision"""
        try:
            command.upgrade(self.alembic_cfg, revision)
            logger.info(f"Database upgraded to {revision}")
        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            raise
    
    def downgrade_database(self, revision: str):
        """Downgrade database to specified revision"""
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Database downgraded to {revision}")
        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision"""
        try:
            with db_manager.session_scope() as session:
                context = MigrationContext.configure(session.connection())
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None


# Global database manager instance
db_manager = DatabaseManager()

# Global migration manager instance
migration_manager = MigrationManager()

# Legacy compatibility
engine = db_manager.engine
SessionLocal = db_manager.session_factory
metadata = Base.metadata


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session (FastAPI compatible)"""
    with db_manager.session_scope() as session:
        yield session


def get_db_session() -> Session:
    """Get database session for non-async operations"""
    return db_manager.get_session()


async def init_db():
    """Initialize database tables"""
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def test_database_connection() -> bool:
    """Test database connection"""
    return db_manager.test_connection()


def create_migration(message: str):
    """Create a new database migration"""
    migration_manager.create_migration(message)


def upgrade_database(revision: str = "head"):
    """Upgrade database to latest version"""
    migration_manager.upgrade_database(revision)


def get_database_info() -> dict:
    """Get database information"""
    return {
        "url": db_manager.database_url.split("://")[0] + "://***",  # Hide credentials
        "tables": db_manager.get_table_info(),
        "current_revision": migration_manager.get_current_revision(),
        "connection_pool_size": db_manager.engine.pool.size() if hasattr(db_manager.engine.pool, 'size') else "N/A",
        "connection_pool_checked_out": db_manager.engine.pool.checkedout() if hasattr(db_manager.engine.pool, 'checkedout') else "N/A"
    }
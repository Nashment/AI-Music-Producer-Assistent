"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings


class Database:
    """
    Database connection manager
    """

    def __init__(self, database_url: str = None):
        """
        Initialize database
        
        Args:
            database_url: Database connection string
        """
        self.database_url = database_url or settings.DATABASE_URL
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=settings.DB_ECHO,
            pool_pre_ping=True,  # Verify connections are alive
            pool_size=10,
            max_overflow=20,
        )
        
        # Create async session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Prevent lazy loading issues after commit
        )

    def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.SessionLocal()

    async def init_db(self):
        """Initialize database tables"""
        from app.data.models import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized")

    async def close_db(self):
        """Close database connection"""
        await self.engine.dispose()

    async def health_check(self) -> bool:
        """Check database connection health"""
        from sqlalchemy import text  # Necessário para o SELECT 1 no SQLAlchemy 2.0+

        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False

# Global database instance
db = Database()

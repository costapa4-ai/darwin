from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseConnection:
    """
    Manages the database connection using SQLAlchemy and connection pooling.

    Attributes:
        engine: SQLAlchemy engine instance.
        SessionLocal: SQLAlchemy session maker.
    """

    def __init__(self, db_url: str, pool_size: int = 5, max_overflow: int = 10, pool_recycle: int = 3600):
        """
        Initializes the database connection with connection pooling.

        Args:
            db_url: The database connection string.
            pool_size: The size of the connection pool. Defaults to 5.
            max_overflow: The maximum overflow of connections in the pool. Defaults to 10.
            pool_recycle: The number of seconds after which a connection is recycled. Defaults to 3600.
        """
        try:
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logging.info("Database connection pool initialized successfully.")
        except Exception as e:
            logging.error(f"Error initializing database connection: {e}")
            raise

    def get_session(self) -> Session:
        """
        Returns a new database session.

        Returns:
            A SQLAlchemy Session instance.
        """
        return self.SessionLocal()

    def execute_query(self, query: str, parameters: Optional[dict] = None) -> Any:
        """
        Executes a SQL query.

        Args:
            query: The SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            The result of the query execution.

        Raises:
            Exception: If there is an error executing the query.
        """
        session = self.get_session()
        try:
            result = session.execute(text(query), parameters)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logging.error(f"Error executing query: {e}")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """
        Disposes of the connection pool.
        """
        try:
            self.engine.dispose()
            logging.info("Database connection pool disposed.")
        except Exception as e:
            logging.error(f"Error disposing database connection pool: {e}")

# Example Usage (replace with your actual database URL)
if __name__ == '__main__':
    db_url = "postgresql://user:password@host:port/database"  # Replace with your actual database URL
    db_connection = DatabaseConnection(db_url=db_url)

    try:
        # Example query
        result = db_connection.execute_query("SELECT 1")
        print(f"Query result: {result.scalar()}")

        # Another example with parameters
        result = db_connection.execute_query("SELECT :value", parameters={"value": "test"})
        print(f"Query result with parameters: {result.scalar()}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db_connection.close()
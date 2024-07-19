import os
import mysql.connector
from typing import List, Any, Optional
from dotenv import load_dotenv
from app.db.collection_manager import CollectionManager
from app.models.api import RecordInDb, StatusEnum
from app.logs.logger import get_logger

logger = get_logger(__name__)
load_dotenv()


class MySQLConnection:
    def __init__(self):
        config = {
            'user': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_DATABASE'),
            'port': int(os.getenv('DB_PORT', 3306))
        }
        try:
            db = mysql.connector.connect(**config)
            self.db = db
            logger.info("Connection successful")
        except mysql.connector.Error as error:
            logger.info("Error in database connection:", error)

    def __enter__(self):
        return self.db

    def __exit__(self):
        if self.db:
            self.db.close()

    def query_db(self, table_name: str, col_names: List[str]) -> Optional[List[RecordInDb]]:
        if not self.db:
            logger.error("No database connection")
            return None

        # Validate table name against MAPPING.keys()
        if not self._is_valid_table_name(table_name):
            logger.error(f"Invalid table name: {table_name}")
            return None

        cursor = self.db.cursor(dictionary=True)
        try:
            col_names_str = ', '.join([f"{col}" for col in col_names])
            query = f"SELECT {col_names_str} FROM {table_name}"
            cursor.execute(query)
            results: List[Any] = cursor.fetchall()
            records = [
                RecordInDb(
                    id=str(result[col_names[0]]),
                    name=result[col_names[1]],
                    description=result[col_names[2]],
                    status=StatusEnum(str(result[col_names[3]])) if result[col_names[3]] else None
                ) for result in results
            ]
            return records
        except mysql.connector.Error as error:
            logger.error("Error querying database:", error)
            return []
        finally:
            cursor.close()

    @staticmethod
    def _is_valid_table_name(table_name: str) -> bool:
        collection_manager = CollectionManager()
        return table_name in collection_manager.get_used_collections().keys()

    def list_tables(self) -> List[str]:
        cursor = self.db.cursor()
        try:
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]  # type: ignore
            return tables  # type: ignore
        except mysql.connector.Error as error:
            logger.error("Error in listing tables:", error)
            return []
        finally:
            if cursor:
                cursor.close()

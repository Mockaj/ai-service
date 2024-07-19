from app.logs.logger import get_logger
from app.db.elastic import Elastic
from functools import wraps
from typing import Callable

logger = get_logger(__name__)


def manage_es_index(test_func: Callable, test_index: str = "test_index") -> Callable:
    @wraps(test_func)
    async def wrapper(*args, **kwargs):
        # Create an instance of the Elastic class
        elastic = Elastic()
        index_exists = await elastic.client.indices.exists(index=test_index)
        if index_exists:
            await elastic.client.indices.delete(index=test_index)
            logger.info(f"Successfully deleted {test_index}")
        await elastic.create_index(index_name=test_index)
        logger.info(f"Successfully created {test_index}")

        try:
            # Run the test function
            await test_func(*args, **kwargs)
        finally:
            # Delete the test index after the test
            await elastic.client.indices.delete(index=test_index)
            logger.info(f"Successfully deleted {test_index}")
            await elastic.client.close()

    return wrapper

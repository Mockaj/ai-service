import asyncio
import uuid
from typing import List, Dict
from app.models.api import RecordInDb
from app.db.crm_db import MySQLConnection
from app.db.elastic import Elastic
from app.db.collection_manager import CollectionManager
from app.logs.logger import get_logger

logger = get_logger(__name__)


def get_record_keys() -> List[str]:
    return list(RecordInDb.model_fields.keys())


async def get_data(tables: List[str]) -> Dict[str, List[RecordInDb]]:
    all_data: Dict[str, List[RecordInDb]] = {}
    db = MySQLConnection()

    try:
        record_keys = get_record_keys()
        for table in tables:
            queried_data = db.query_db(table, record_keys)
            if queried_data:
                all_data[table] = queried_data
                logger.info(f"Fetched {len(queried_data)} records for table: {table}")
            else:
                logger.warning(f"No data fetched for table: {table}")
    except Exception as e:
        logger.error(f"Error fetching data: {e}", exc_info=True)
        raise
    finally:
        if db:
            db.__exit__()

    return all_data


async def seed_elastic() -> None:
    es = Elastic()
    try:
        collection_manager = CollectionManager()
        data_mapping = collection_manager.get_used_collections()
        my_sql_tables = list(data_mapping.keys())
        elastic_tables = list(data_mapping.values())
        data = await get_data(my_sql_tables)

        for my_sql_table, elastic_table in zip(my_sql_tables, elastic_tables):
            # Use a unique name for the temporary index to avoid conflicts
            temp_index = f"{elastic_table}_temp_{uuid.uuid4()}"
            backup_index = f"{elastic_table}_backup"

            # Create the temporary index
            logger.info(f"Creating index: {temp_index}")
            await es.create_index(temp_index)

            # Populate the temporary index with data
            logger.info(f"Populating {temp_index} with {len(data[my_sql_table])} records")
            await es.populate_es(temp_index, data[my_sql_table])

            # Check if an alias exists for the current index
            alias_exists = await es.client.indices.exists_alias(name=elastic_table)

            if alias_exists:
                # Retrieve the old index name associated with the alias
                old_index = await es.client.indices.get_alias(name=elastic_table)
                old_index_name = list(old_index.keys())[0]
                logger.info(f"Switching alias {elastic_table} from {old_index_name} to {temp_index}")

                # Update the alias to point to the new index
                await es.client.indices.update_aliases(body={
                    "actions": [
                        {"remove": {"index": old_index_name, "alias": elastic_table}},
                        {"add": {"index": temp_index, "alias": elastic_table}}
                    ]
                })

                # Check if the backup index exists and delete it if it does
                if await es.client.indices.exists(index=backup_index):
                    logger.info(f"Deleting old backup index: {backup_index}")
                    await es.delete_index(backup_index)

                # Rename the old index to the backup index
                logger.info(f"Renaming old index {old_index_name} to backup index {backup_index}")
                await es.client.reindex(body={
                    "source": {"index": old_index_name},
                    "dest": {"index": backup_index}
                }, wait_for_completion=True)

                # Delete the old index after creating the backup alias
                await es.delete_index(old_index_name)
            else:
                # If no alias exists, just create alias for the new index
                logger.info(f"Creating alias {elastic_table} for {temp_index}")
                await es.client.indices.put_alias(index=temp_index, name=elastic_table)

            # Cleanup old temporary indices (if any)
            for index in await es.client.indices.get(index=f"{elastic_table}_temp_*"):
                if index != temp_index:
                    logger.info(f"Deleting old temporary index: {index}")
                    await es.delete_index(index)

        logger.info("Data sync complete")
    except Exception as e:
        logger.error(f"Error during Elasticsearch seeding: {e}", exc_info=True)
        raise
    finally:
        await es.client.close()


if __name__ == "__main__":
    asyncio.run(seed_elastic())

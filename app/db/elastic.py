import os
import sys
import aiohttp
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch, NotFoundError, ApiError
from app.config import VECTOR_DIMENSION as DIMENSION
from app.modules.embedding_model import get_embedding
from app.models.api import RecordCreateReplace, RecordDelete, RecordPatch, RecordInDb
from app.models.elastic import ElasticSearchResponse, Hit
from app.db.utils import clean_elastic_response, elastic_search_response_is_empty
from app.logs.logger import get_logger

logger = get_logger(__name__)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

load_dotenv()
ELASTICSEARCH_CLOUD_ID = os.getenv('ELASTICSEARCH_CLOUD_ID')
ELASTICSEARCH_API_KEY = os.getenv('ELASTICSEARCH_API_KEY')


class Elastic:
    def __init__(self):
        self.client = AsyncElasticsearch(cloud_id=ELASTICSEARCH_CLOUD_ID,
                                         api_key=ELASTICSEARCH_API_KEY)

    async def create_index(self, index_name: str, vector_dim: int = DIMENSION) -> None:
        try:
            if not await self.client.indices.exists(index=index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text"},
                            "description": {"type": "text"},
                            "status": {"type": "keyword"},
                            "vector": {
                                "type": "dense_vector",
                                "dims": vector_dim
                            }
                        }
                    }
                }
                await self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"Index '{index_name}' created with vector dimension {vector_dim}")
            else:
                logger.info(f"Index '{index_name}' already exists")
        except Exception as e:
            logger.error(f"Error creating index '{index_name}': {e}", exc_info=True)
            raise e

    async def populate_es(self, index_name: str, data: List[RecordInDb]) -> None:
        for item in data:
            try:
                vector = await get_embedding([item.name])
                doc = {
                    **item.model_dump(),
                    'vector': vector[0]
                }
                await self.client.index(index=index_name, document=doc)
            except Exception as e:
                logger.error(f"Error indexing document {item.id}: {e}")
        logger.info(f"Data populated in index '{index_name}'")

    async def find_record_by_doc_id(self, index_name: str, doc_id: str) -> Optional[Hit]:
        try:
            response = await self.client.get(index=index_name, id=doc_id)
            return Hit(index=response['_index'], id=response['_id'], source=response['_source'])
        except NotFoundError as e:
            logger.error(f"Error getting index '{index_name}': {e} for doc_id: {doc_id}")
            return None

    async def query_es(self, index_name: str, query: Optional[Dict[str, Any]] = None) -> Optional[
        ElasticSearchResponse]:
        try:
            response = await self.client.search(index=index_name, body=query)
            if elastic_search_response_is_empty(response):
                logger.info(f"No results found in index '{index_name}' for query '{query}'")
                return None
            else:
                cleaned_response = clean_elastic_response(response)
                return cleaned_response
        except Exception as e:
            logger.error(f"Error querying index '{index_name}' for query '{query}': {e}")
            return None

    async def similarity_search(self, index_name: str, text: str, top_n: int = 1) -> Optional[ElasticSearchResponse]:
        try:
            query_vector = await get_embedding([text])
            query: Any = {
                "size": top_n,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'vector')",
                            "params": {"query_vector": query_vector[0]}
                        }
                    }
                }
            }
            results = await self.query_es(index_name, query)
            logger.info(f"Performed similarity search for index '{index_name}' with text '{text}'")
            return results
        except Exception as e:
            logger.error(f"Error performing similarity search in index '{index_name}' for text: '{text}': {e}")
            return None

    async def create_replace_record(self, collection_name: str, record: RecordCreateReplace) -> str:
        try:
            logger.info(f"Starting create_replace_record for collection: {collection_name}, record: {record}")

            # Embedding vector
            vector = await get_embedding([record.name])
            logger.info(f"Embedding vector obtained: {vector}")

            doc = {
                **record.model_dump(),
                'vector': vector[0]
            }
            logger.info(f"Document to be indexed: {doc}")

            # Query for existing record by ID
            query: Any = {
                "query": {
                    "term": {
                        "id": record.id
                    }
                }
            }
            logger.info(f"Query to search for the existing record: {query}")

            response = await self.client.search(index=collection_name, body=query)
            logger.info(f"Elasticsearch search response: {response}")

            doc_id: Optional[str] = None

            if response['hits']['hits']:
                doc_id = response['hits']['hits'][0]['_id']
                action = 'replaced'
            else:
                action = 'created'
            logger.info(f"Action to be performed: {action}, doc_id: {doc_id}")

            # Indexing the document: create or replace
            saved_record = await self.client.index(index=collection_name, document=doc, id=doc_id)
            logger.info(f"Record {action} successfully with ID: {saved_record['_id']}")
            return saved_record['_id']

        except ApiError as e:
            logger.error(f"Failed to create or replace record: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}", exc_info=True)
            raise e

    async def partial_update_record(self, collection_name: str, record: RecordPatch) -> Optional[str]:
        try:
            query: Any = {
                "query": {
                    "term": {
                        "id": record.id
                    }
                }
            }

            response = await self.client.search(index=collection_name, body=query)
            update_fields = record.model_dump(exclude_unset=True, exclude={"id"}, exclude_none=True)

            if not elastic_search_response_is_empty(response):
                doc_id = response['hits']['hits'][0]['_id']
                update = await self.client.update(index=collection_name, id=doc_id, body={"doc": update_fields})
                logger.info(f"Updated document with ID: {doc_id}")
                return update['_id']

            logger.info(f"No document found with id {record.id} in index {collection_name}")
            return None
        except ApiError as e:
            logger.error(f"Failed to update record '{record}' in index {collection_name}': {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error occurred for record {record}' in index {collection_name}': {e}")
            raise e

    async def delete_record(self, collection_name: str, record: RecordDelete) -> None:
        try:
            query = {
                "query": {
                    "term": {
                        "id": record.id
                    }
                }
            }
            response = await self.client.search(index=collection_name, body=query)

            if not elastic_search_response_is_empty(response):
                doc_id = response['hits']['hits'][0]['_id']
                await self.client.delete(index=collection_name, id=doc_id)
                logger.info(f"Deleted document with ID: {doc_id}")
            else:
                logger.info(f"No document found with id {record.id} in index {collection_name}")
        except ApiError as e:
            logger.error(f"Failed to delete record '{record}' in index {collection_name}': {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error occurred for record {record}' in index {collection_name}': {e}")
            raise e

    async def delete_index(self, index_name: str) -> None:
        try:
            if await self.client.indices.exists(index=index_name):
                await self.client.indices.delete(index=index_name)
                logger.info(f"Index '{index_name}' deleted successfully.")
            else:
                logger.info(f"Index '{index_name}' does not exist.")
        except NotFoundError:
            logger.warning(f"Index '{index_name}' not found.")
        except ApiError as e:
            logger.error(f"Elasticsearch error occurred: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise e

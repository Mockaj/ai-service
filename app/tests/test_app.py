import sys
import os
import requests
import pytest
from app.db.elastic import Elastic
from app.logs.logger import get_logger
from app.tests.utils import manage_es_index
from dotenv import load_dotenv

logger = get_logger(__name__)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:9900/api/v1/")


def url(endpoint: str) -> str:
    return f"{BASE_URL}{endpoint}"


def test_monitoring_endpoint():
    response = requests.get(url(endpoint="monitoring"))
    assert response.status_code == 200
    json_response = response.json()
    assert "elastic" in json_response
    assert json_response["elastic"] == "success"


def test_collections_endpoint():
    response = requests.get(url(endpoint="collections"))
    assert response.status_code == 200
    json_response = response.json()
    assert "collections" in json_response
    assert set(json_response["collections"]) == {"skills", "markets", "industries", "specialisms"}


def test_find_similar_records():
    payload = {
        "query": ["Python"]
    }
    endpoint = url("collections/skills/similarities?top_n=1")
    response = requests.post(endpoint, json=payload)
    json_response = response.json()
    assert "data" in json_response
    assert any(record["name"] == "Python" for record in json_response["data"])


ID = "9999999"
TEST_INDEX = "test_index"
PREFIX = "embeddings_"


@pytest.mark.asyncio
@manage_es_index
async def test_sync_post_record():
    payload = {
        "payload": [
            {
                "data": {
                    "id": ID,
                    "method": "POST",
                    "name": "AI expert",
                    "description": "string",
                    "status": "1"
                }
            }
        ]
    }
    endpoint = url(f"collections/{TEST_INDEX}/sync")
    response = requests.post(endpoint, json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
@manage_es_index
async def test_sync_put_record():
    payload = {
        "payload": [
            {
                "data": {
                    "id": ID,
                    "method": "PUT",
                    "name": "Updated Test Record",
                    "description": "Updated description",
                    "status": "1"
                }
            }
        ]
    }
    response = requests.post(url(f"collections/{TEST_INDEX}/sync"), json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
@manage_es_index
async def test_sync_patch_record():
    payload = {
        "payload": [
            {
                "data": {
                    "id": ID,
                    "method": "PATCH",
                    "name": "Partially Updated Test Record"
                }
            }
        ]
    }
    response = requests.post(url(f"collections/{TEST_INDEX}/sync"), json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
@manage_es_index
async def test_sync_delete_record():
    payload = {
        "payload": [
            {
                "data": {
                    "id": "99999",
                    "method": "DELETE"
                }
            }
        ]
    }
    response = requests.post(url(f"collections/{TEST_INDEX}/sync"), json=payload)
    if response.status_code != 200:
        logger.info(f"Failed with response: {response.status_code}, {response.text}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_collections_index_existence():
    response = requests.get(url("collections"))
    assert response.status_code == 200
    collections = response.json().get("collections", [])

    elastic = Elastic()
    for collection in collections:
        prefixed_collection = f"{PREFIX}{collection}"
        index_exists = await elastic.client.indices.exists(index=prefixed_collection)
        assert index_exists, f"Index '{prefixed_collection}' does not exist in ElasticSearch"

        alias_exists = await elastic.client.indices.exists_alias(name=prefixed_collection)
        assert alias_exists, f"Alias '{prefixed_collection}' does not exist in ElasticSearch"
    await elastic.client.close()


@pytest.mark.asyncio
async def test_collection_alias_existence():
    response = requests.get(url("collections"))
    assert response.status_code == 200
    collections = response.json().get("collections", [])

    elastic = Elastic()
    for collection in collections:
        prefixed_collection = f"{PREFIX}{collection}"
        alias = await elastic.client.indices.get_alias(name=prefixed_collection)
        aliases = []
        for value in alias.values():
            aliases.extend(value['aliases'].keys())
        assert prefixed_collection in aliases, f"Alias '{prefixed_collection}' does not exist for any index"
    await elastic.client.close()

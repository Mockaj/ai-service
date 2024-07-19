from app.utils import read_logs_once
from pydantic import ValidationError
from fastapi import APIRouter, FastAPI, Query
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from app.models.api import (RecordInDb, RecordDelete, RecordPatch, RecordCreateReplace, SimilarRecordsQuery,
                            SimilarRecordsResponse,
                            ErrorResponse, GetCollectionsResponse, SyncRecordsPayload, SimilarRecord)
from app.db.elastic import Elastic
from app.db.collection_manager import CollectionManager, PREFIX

app = FastAPI(
    title="ai-service",
    description="API for searching for similar records in CRM database (such as skills, markets, industries, etc..) and synchronizing data.",
    version="1.0"
)
router = APIRouter()
es = Elastic()


@router.get(path="/collections",
            summary="List all collections",
            description="Returns an object containing an array of strings, each representing a collection name.",
            response_model=GetCollectionsResponse,
            responses={500: {"model": ErrorResponse}, 200: {"model": GetCollectionsResponse}}
            )
async def list_collections() -> GetCollectionsResponse:
    try:
        collection_manager = CollectionManager()
        elastic_tables = collection_manager.get_used_collections()
        response: list[str] = []
        for table in elastic_tables.values():
            if not await es.client.indices.exists(index=table):
                raise ValueError(f"Index '{table}' not found")
            response.append(table.removeprefix(PREFIX))
        return GetCollectionsResponse(collections=response, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(path="/collections/{collection_name}/sync",
             summary="Synchronize records",
             description="Synchronize records within the specified collection. The method of synchronization (POST, PUT, PATCH, DELETE) determines the action performed on the records.",
             response_model=dict,
             responses={200: {"success": "Data received successfully"}, 500: {"model": ErrorResponse}})
async def sync(collection_name: str, sync_records: SyncRecordsPayload):
    try:
        collection_manager = CollectionManager()
        collections = collection_manager.get_all_collections()  # Getting all collections for tests
        collection_name = collections[collection_name]
        for record in sync_records.payload:
            match record.data.method:
                case 'POST' | 'PUT':
                    record_create_replace = RecordCreateReplace(**record.data.model_dump())
                    await es.create_replace_record(collection_name, record_create_replace)
                case 'PATCH':
                    record_patch = RecordPatch(**record.data.model_dump())
                    await es.partial_update_record(collection_name, record_patch)
                case 'DELETE':
                    record_delete = RecordDelete(**record.data.model_dump())
                    await es.delete_record(collection_name, record_delete)
                case _:
                    raise ValueError('Invalid method')
        return {"message": "Data received successfully"}
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(path="/collections/{collection_name}/similarities",
             response_model=SimilarRecordsResponse,
             summary="Find top_n most similar records",
             description="Returns the top_n most similar records from the specified collection based on a query string."
                         "The query string must not be empty and must comply with maximum length.",
             responses={200: {"description": "A list of similar records"}, 400: {"model": ErrorResponse},
                        404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def find_similar_records(collection_name: str, query_data: SimilarRecordsQuery, top_n: int = 1) -> (
        SimilarRecordsResponse):
    try:
        collection_manager = CollectionManager()
        collections = collection_manager.get_used_collections()
        collection_name = collections[collection_name]
        response = SimilarRecordsResponse(data=[])
        for text in query_data.query:
            elastic_response = await es.similarity_search(collection_name, text, top_n)
            if elastic_response:
                for hit in elastic_response.hits.hits:
                    record = SimilarRecord(**hit.source.model_dump(), score=hit.score)
                    response.data.append(record)
        return response

    except Exception as e:
        if "not found" in str(object=e).lower():
            raise HTTPException(status_code=404, detail="Collection not found")
        elif isinstance(e, ValidationError):
            raise HTTPException(
                status_code=400, detail="Invalid input parameters or query issues")
        else:
            raise HTTPException(status_code=500, detail=str(e))


async def health_check():
    return True


@router.get(path="/monitoring")
async def ping():
    elastic = "success" if await es.client.ping() else "an error has occurred while connecting to Elasticsearch"
    ai_service = "success" if await health_check() else "an error has occurred while connecting to AI service"
    return {"elastic": elastic, "ai-service": ai_service}


@router.get(path="/logs", response_class=HTMLResponse)
async def info(n: int = Query(10, description="Number of lines of stdout to retrieve")):
    logs = read_logs_once(n)
    log_lines = logs.split('\n')  # Assuming logs is a single string with newline characters

    # Create HTML content
    html_content = """
    <html>
        <head>
            <title>Logs</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                pre { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Application Logs</h1>
            <pre>"""
    for line in log_lines:
        html_content += f"{line.lstrip()}\n"
    html_content += """
            </pre>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content)


app.include_router(router=router, prefix="/api/v1", tags=["v1"])

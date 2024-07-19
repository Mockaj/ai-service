from typing import Any
from app.models.elastic import ElasticSearchResponse, Shards, Hits, Hit, TotalHits


def clean_elastic_response(response: Any) -> ElasticSearchResponse:
    took = response['took']
    timed_out = response['timed_out']
    _shards = Shards(total=response['_shards']['total'],
                     successful=response['_shards']['successful'],
                     skipped=response['_shards']['skipped'],
                     failed=response['_shards']['failed'])
    hits = Hits(
        total=TotalHits(
            value=response['hits']['total']['value'],
            relation=response['hits']['total']['relation']),
        max_score=response['hits']['max_score'],
        hits=[Hit(index=hit['_index'], id=hit['_id'],
                  score=hit['_score'],
                  source=hit['_source']) for hit in response['hits']['hits']])
    response = ElasticSearchResponse(took=took, timed_out=timed_out, shards=_shards, hits=hits)
    return response


def elastic_search_response_is_empty(response: Any) -> bool:
    return response['hits']['total']['value'] == 0

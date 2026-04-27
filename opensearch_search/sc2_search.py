# SC2 Bot - OpenSearch Full-Text & Vector Search
# Replay search, game event queries, strategy similarity via k-NN

import json
from typing import Any, Dict, List

from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk

# --- Client Setup ---
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    connection_class=RequestsHttpConnection,
)

# --- Index: sc2-replays ---
SC2_REPLAY_INDEX = "sc2-replays"
SC2_REPLAY_MAPPING = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "knn": True,
    },
    "mappings": {
        "properties": {
            "replay_id": {"type": "keyword"},
            "map_name": {"type": "keyword"},
            "player_race": {"type": "keyword"},
            "opponent_race": {"type": "keyword"},
            "result": {"type": "keyword"},  # "win" | "loss"
            "game_duration": {"type": "integer"},
            "timestamp": {"type": "date"},
            "build_order": {"type": "text", "analyzer": "english"},
            "events": {"type": "text", "analyzer": "standard"},
            "strategy_tags": {"type": "keyword"},
            # k-NN vector field for strategy similarity
            "strategy_vector": {
                "type": "knn_vector",
                "dimension": 128,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
        }
    },
}


def create_index():
    if not client.indices.exists(SC2_REPLAY_INDEX):
        client.indices.create(index=SC2_REPLAY_INDEX, body=SC2_REPLAY_MAPPING)
        print(f"[OpenSearch] Created index: {SC2_REPLAY_INDEX}")


# --- Index Replay Docs ---
def index_replay(replay: dict):
    client.index(
        index=SC2_REPLAY_INDEX, id=replay["replay_id"], body=replay, refresh=True
    )


def bulk_index_replays(replays: List[dict]):
    actions = [
        {"_index": SC2_REPLAY_INDEX, "_id": r["replay_id"], "_source": r}
        for r in replays
    ]
    bulk(client, actions, refresh=True)


# --- Queries ---
def search_by_build_order(query_text: str, size: int = 10) -> List[dict]:
    """Full-text match on build_order and events fields."""
    body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["build_order^2", "events", "strategy_tags"],
            }
        },
        "highlight": {"fields": {"build_order": {}, "events": {}}},
    }
    resp = client.search(index=SC2_REPLAY_INDEX, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def search_win_replays(race: str, min_duration: int = 300) -> List[dict]:
    """Bool query: win replays by race with minimum duration."""
    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"result": "win"}},
                    {"term": {"player_race": race}},
                ],
                "filter": [{"range": {"game_duration": {"gte": min_duration}}}],
            }
        },
        "sort": [{"game_duration": {"order": "desc"}}],
    }
    resp = client.search(index=SC2_REPLAY_INDEX, body=body)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def aggregate_win_rates_by_matchup() -> dict:
    """Aggregation: win rate per player_race x opponent_race matchup."""
    body = {
        "size": 0,
        "aggs": {
            "by_matchup": {
                "composite": {
                    "sources": [
                        {"player_race": {"terms": {"field": "player_race"}}},
                        {"opponent_race": {"terms": {"field": "opponent_race"}}},
                    ]
                },
                "aggs": {
                    "total": {"value_count": {"field": "replay_id"}},
                    "wins": {"filter": {"term": {"result": "win"}}},
                    "avg_duration": {"avg": {"field": "game_duration"}},
                },
            }
        },
    }
    resp = client.search(index=SC2_REPLAY_INDEX, body=body)
    return resp["aggregations"]


def knn_similar_strategies(vector: List[float], k: int = 5) -> List[dict]:
    """k-NN vector search: find replays with similar strategy embeddings."""
    body = {
        "size": k,
        "query": {
            "knn": {
                "strategy_vector": {
                    "vector": vector,
                    "k": k,
                }
            }
        },
    }
    resp = client.search(index=SC2_REPLAY_INDEX, body=body)
    return [
        {"id": h["_id"], "score": h["_score"], **h["_source"]}
        for h in resp["hits"]["hits"]
    ]

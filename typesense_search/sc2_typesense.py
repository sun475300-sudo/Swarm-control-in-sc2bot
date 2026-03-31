# SC2 Bot - Typesense Vector + Full-Text Hybrid Search
# Build order collection with BM25 + semantic vector hybrid search

import typesense
from typing import List, Optional, Dict, Any

# --- Client Setup ---
client = typesense.Client({
    "api_key": "sc2-typesense-api-key",
    "nodes": [{"host": "localhost", "port": "8108", "protocol": "http"}],
    "connection_timeout_seconds": 5,
})

# --- Collection: sc2_builds ---
SC2_BUILDS_SCHEMA = {
    "name": "sc2_builds",
    "fields": [
        {"name": "id",              "type": "string"},
        {"name": "build_name",      "type": "string"},
        {"name": "race",            "type": "string",  "facet": True},
        {"name": "matchup",         "type": "string",  "facet": True},
        {"name": "description",     "type": "string"},
        {"name": "tags",            "type": "string[]", "facet": True},
        {"name": "win_rate",        "type": "float",   "facet": False},
        {"name": "rating",          "type": "float"},
        {"name": "difficulty",      "type": "string",  "facet": True},
        {"name": "is_meta",         "type": "bool",    "facet": True},
        # Semantic vector field (1536-dim for OpenAI, 384-dim for sentence-transformers)
        {
            "name": "embedding",
            "type": "float[]",
            "num_dim": 384,
            "embed": {
                "from": ["build_name", "description", "tags"],
                "model_config": {
                    "model_name": "ts/all-MiniLM-L6-v2"
                },
            },
        },
    ],
    "default_sorting_field": "rating",
    "token_separators": ["-", "_"],
    "symbols_to_index": ["+"],
}

def create_collection():
    try:
        client.collections["sc2_builds"].retrieve()
        print("[Typesense] Collection already exists.")
    except typesense.exceptions.ObjectNotFound:
        client.collections.create(SC2_BUILDS_SCHEMA)
        print("[Typesense] Created collection: sc2_builds")

def add_builds(builds: List[dict]):
    resp = client.collections["sc2_builds"].documents.import_(builds, {"action": "upsert"})
    failed = [r for r in resp if not r.get("success", True)]
    if failed:
        print(f"[Typesense] {len(failed)} docs failed to import")
    else:
        print(f"[Typesense] Imported {len(builds)} builds")

# --- Hybrid Search: BM25 + Semantic Vector ---
def hybrid_search(
    query: str,
    race: Optional[str] = None,
    matchup: Optional[str] = None,
    min_win_rate: float = 0.0,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Hybrid search combining BM25 keyword and semantic vector search."""
    filter_parts = [f"win_rate:>={min_win_rate}"]
    if race:
        filter_parts.append(f"race:={race}")
    if matchup:
        filter_parts.append(f"matchup:={matchup}")

    return client.collections["sc2_builds"].documents.search({
        "q": query,
        "query_by": "build_name, description, embedding",
        "query_by_weights": "2, 1, 1",   # BM25 weighted higher on name
        "vector_query": f"embedding:([], alpha:0.5)",  # 50% BM25 + 50% vector
        "filter_by": " && ".join(filter_parts),
        "sort_by": "_text_match:desc, rating:desc",
        "facet_by": "race, matchup, difficulty, is_meta",
        "page": page,
        "per_page": per_page,
        "highlight_full_fields": "build_name, description",
        "num_typos": 2,
    })

def filter_by_matchup_sorted_by_rating(matchup: str, limit: int = 10) -> dict:
    """Geo-style sort by rating, filter by matchup."""
    return client.collections["sc2_builds"].documents.search({
        "q": "*",
        "filter_by": f"matchup:={matchup}",
        "sort_by": "rating:desc, win_rate:desc",
        "per_page": limit,
    })

# --- Sample Usage ---
if __name__ == "__main__":
    create_collection()
    builds = [
        {"id": "1", "build_name": "Ling Bane Muta", "race": "Zerg", "matchup": "ZvT",
         "description": "Standard ZvT macro build with Ling Bane Muta transition",
         "tags": ["macro", "ling", "bane", "muta"], "win_rate": 0.58, "rating": 8.5,
         "difficulty": "hard", "is_meta": True},
        {"id": "2", "build_name": "Mass Roach", "race": "Zerg", "matchup": "ZvP",
         "description": "Roach all-in timing attack vs Protoss",
         "tags": ["all-in", "roach"], "win_rate": 0.52, "rating": 7.0,
         "difficulty": "medium", "is_meta": False},
    ]
    add_builds(builds)
    results = hybrid_search("ling bane macro", race="Zerg")
    print(f"[Typesense] Hits: {results['found']}")
    for hit in results["hits"]:
        print(f"  - {hit['document']['build_name']} score={hit.get('text_match_info', {}).get('score', 'N/A')}")

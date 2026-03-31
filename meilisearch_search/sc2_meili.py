# SC2 Bot - Meilisearch Instant Search
# Strategy database with faceted search, filtering, and typo tolerance

import meilisearch
from typing import List, Dict, Any, Optional

# --- Client Setup ---
client = meilisearch.Client("http://localhost:7700", "sc2-meili-master-key")

# --- Index: sc2-strategies ---
INDEX_NAME = "sc2-strategies"
index = client.index(INDEX_NAME)

# --- Index Settings ---
INDEX_SETTINGS = {
    "searchableAttributes": [
        "strategy_name",
        "description",
        "build_order_text",
        "tags",
    ],
    "filterableAttributes": [
        "race",
        "matchup",
        "difficulty",
        "win_rate",
        "is_meta",
    ],
    "sortableAttributes": [
        "win_rate",
        "popularity_score",
        "last_updated",
    ],
    "displayedAttributes": [
        "id", "strategy_name", "race", "matchup", "description",
        "win_rate", "difficulty", "tags", "build_order_text", "is_meta",
    ],
    "rankingRules": [
        "words", "typo", "proximity", "attribute", "sort", "exactness",
        "win_rate:desc",
    ],
    "typoTolerance": {
        "enabled": True,
        "minWordSizeForTypos": {"oneTypo": 5, "twoTypos": 9},
    },
    "faceting": {
        "maxValuesPerFacet": 50,
    },
    "pagination": {
        "maxTotalHits": 1000,
    },
}

def configure_index():
    """Apply settings to the sc2-strategies index."""
    task = index.update_settings(INDEX_SETTINGS)
    print(f"[Meilisearch] Settings update task: {task}")

# --- Data Loading ---
def add_strategies(strategies: List[dict]):
    """Bulk add strategies to the index."""
    task = index.add_documents(strategies, primary_key="id")
    print(f"[Meilisearch] Added {len(strategies)} docs, task: {task}")

# --- Search Functions ---
def search_strategies(
    query: str,
    race: Optional[str] = None,
    min_win_rate: Optional[float] = None,
    difficulty: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Instant search with optional filters."""
    filters = []
    if race:
        filters.append(f'race = "{race}"')
    if min_win_rate is not None:
        filters.append(f"win_rate >= {min_win_rate}")
    if difficulty:
        filters.append(f'difficulty = "{difficulty}"')

    params = {
        "limit": limit,
        "offset": offset,
        "attributesToHighlight": ["strategy_name", "description", "build_order_text"],
        "facets": ["race", "matchup", "difficulty"],
        "showRankingScore": True,
    }
    if filters:
        params["filter"] = " AND ".join(filters)

    return index.search(query, params)

def search_meta_strategies(race: str) -> dict:
    """Search for current meta strategies for a race."""
    return index.search("", {
        "filter": f'race = "{race}" AND is_meta = true',
        "sort": ["win_rate:desc"],
        "limit": 10,
    })

def faceted_browse(matchup: str, page: int = 0, hits_per_page: int = 20) -> dict:
    """Faceted browse: all strategies for a matchup with facet counts."""
    return index.search("", {
        "filter": f'matchup = "{matchup}"',
        "facets": ["difficulty", "race"],
        "sort": ["win_rate:desc", "popularity_score:desc"],
        "hitsPerPage": hits_per_page,
        "page": page,
    })

# --- Sample Data ---
SAMPLE_STRATEGIES = [
    {"id": "1", "strategy_name": "6-Pool Rush", "race": "Zerg", "matchup": "ZvT",
     "description": "Aggressive early pool into 6 lings", "win_rate": 0.62,
     "difficulty": "easy", "tags": ["rush", "cheese"], "build_order_text": "6 pool drone pull", "is_meta": False},
    {"id": "2", "strategy_name": "Roach Ravager All-in", "race": "Zerg", "matchup": "ZvP",
     "description": "Roach warren into ravager all-in at 7min", "win_rate": 0.55,
     "difficulty": "medium", "tags": ["all-in", "roach"], "build_order_text": "hatch gas pool roach warren", "is_meta": True},
]

if __name__ == "__main__":
    configure_index()
    add_strategies(SAMPLE_STRATEGIES)
    results = search_strategies("roach", race="Zerg", min_win_rate=0.5)
    print(f"[Meilisearch] Found {results['estimatedTotalHits']} strategies")
    for hit in results["hits"]:
        print(f"  - {hit['strategy_name']} (win_rate={hit['win_rate']})")

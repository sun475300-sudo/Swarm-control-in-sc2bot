# SC2 Bot - Weaviate Advanced: Generative Search & Hybrid Search
# Strategy Q&A with nearText, generative modules, and GraphQL
# Phase 472: Weaviate generative + hybrid search for SC2 strategy Q&A

from typing import List, Optional

import weaviate
from weaviate.classes.config import (
    Configure,
    DataType,
    Property,
    VectorDistances,
)
from weaviate.classes.init import Auth
from weaviate.classes.query import (
    Filter,
    FilterMetadata,
    Generate,
    HybridFusion,
    MetadataQuery,
    NearText,
)

# --- Client Setup (Weaviate Cloud / local) ---
client = weaviate.connect_to_local(
    host="localhost",
    port=8080,
    grpc_port=50051,
    additional_config=weaviate.config.AdditionalConfig(timeout=(10, 60)),
)


# --- Collection: SC2Strategy ---
def create_schema():
    """Create SC2Strategy collection with generative + hybrid search."""
    if client.collections.exists("SC2Strategy"):
        return

    client.collections.create(
        name="SC2Strategy",
        vectorizer_config=Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-small"
        ),
        generative_config=Configure.Generative.openai(model="gpt-4o-mini"),
        properties=[
            Property(name="strategy_name", data_type=DataType.TEXT),
            Property(name="race", data_type=DataType.TEXT),
            Property(name="matchup", data_type=DataType.TEXT),
            Property(name="description", data_type=DataType.TEXT),
            Property(name="build_order", data_type=DataType.TEXT),
            Property(name="win_rate", data_type=DataType.NUMBER),
            Property(name="is_meta", data_type=DataType.BOOL),
            Property(name="tags", data_type=DataType.TEXT_ARRAY),
        ],
        vector_index_config=Configure.VectorIndex.hnsw(
            distance_metric=VectorDistances.COSINE,
            ef_construction=200,
            max_connections=16,
        ),
    )
    print("[Weaviate] Created SC2Strategy collection")


# --- Insert Strategies ---
def insert_strategies(strategies: List[dict]):
    collection = client.collections.get("SC2Strategy")
    with collection.batch.dynamic() as batch:
        for s in strategies:
            batch.add_object(properties=s)
    print(f"[Weaviate] Inserted {len(strategies)} strategies")


# --- nearText Search ---
def near_text_search(concepts: List[str], race: Optional[str] = None, limit: int = 5):
    """Semantic search using nearText."""
    collection = client.collections.get("SC2Strategy")
    filters = None
    if race:
        filters = Filter.by_property("race").equal(race)

    return collection.query.near_text(
        query=concepts,
        filters=filters,
        limit=limit,
        return_metadata=MetadataQuery(distance=True, score=True),
    )


# --- Hybrid Search: BM25 + Vector ---
def hybrid_search(
    query: str, matchup: Optional[str] = None, alpha: float = 0.5, limit: int = 10
):
    """Hybrid search combining BM25 keyword and semantic vector (alpha controls balance)."""
    collection = client.collections.get("SC2Strategy")
    filters = None
    if matchup:
        filters = Filter.by_property("matchup").equal(matchup)

    return collection.query.hybrid(
        query=query,
        alpha=alpha,
        fusion_type=HybridFusion.RELATIVE_SCORE,
        filters=filters,
        limit=limit,
        return_metadata=MetadataQuery(score=True, explain_score=True),
    )


# --- Generative Search: Strategy Q&A ---
def generative_strategy_qa(question: str, race: str, limit: int = 3):
    """Use generative module to answer SC2 strategy questions from retrieved docs."""
    collection = client.collections.get("SC2Strategy")
    return collection.generate.near_text(
        query=[question, race],
        limit=limit,
        single_prompt=(
            f"You are an expert SC2 coach. Based on this strategy: {{description}} "
            f"Answer this question concisely: {question}"
        ),
        grouped_task=(
            f"You are an expert SC2 coach. Given these {race} strategies, "
            f"recommend the best approach for: {question}. "
            "Format as: Strategy Name → Key steps → Win condition"
        ),
        return_metadata=MetadataQuery(distance=True),
    )


# --- Sample Usage ---
if __name__ == "__main__":
    create_schema()
    strategies = [
        {
            "strategy_name": "Ling Bane Muta",
            "race": "Zerg",
            "matchup": "ZvT",
            "description": "Economic macro build transitioning into Ling Bane Muta",
            "build_order": "Pool → Gas → Hatch → Lair → Bane Nest → Spire",
            "win_rate": 0.58,
            "is_meta": True,
            "tags": ["macro", "ling", "bane", "muta"],
        },
    ]
    insert_strategies(strategies)

    results = near_text_search(
        ["aggressive early pressure", "zergling rush"], race="Zerg"
    )
    print(f"[Weaviate] nearText found {len(results.objects)} strategies")

    answer = generative_strategy_qa("How do I beat Terran bio?", "Zerg")
    if answer.generated:
        print(f"[Weaviate Generative] {answer.generated}")

    client.close()

# pinecone_search/strategy_embeddings.py
# Pinecone vector search for SC2 Zerg strategy recommendations

import time
from sentence_transformers import SentenceTransformer
import pinecone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PINECONE_API_KEY = "your-pinecone-api-key-here"
PINECONE_ENV     = "us-east-1-aws"
INDEX_NAME       = "sc2-strategies"
EMBEDDING_DIM    = 384          # all-MiniLM-L6-v2 output dimension
TOP_K            = 5

# ---------------------------------------------------------------------------
# Strategy corpus: 20 Zerg strategies across all matchups
# ---------------------------------------------------------------------------
STRATEGIES = [
    # ZvT openings (7 strategies)
    {"id": "zvt_01", "matchup": "ZvT", "name": "12 Pool Speed",
     "description": "Fast Zergling speed into economical expansion, pressures bio early."},
    {"id": "zvt_02", "matchup": "ZvT", "name": "Roach-Ravager All-In",
     "description": "Mass Roach with Ravager support, hits before Terran mech establishes."},
    {"id": "zvt_03", "matchup": "ZvT", "name": "Ling-Bane Flood",
     "description": "Heavy Zergling and Baneling production to overwhelm bio walls."},
    {"id": "zvt_04", "matchup": "ZvT", "name": "Muta Harass into Ling-Bane",
     "description": "Mutalisks force defensive turrets then transition to ground army."},
    {"id": "zvt_05", "matchup": "ZvT", "name": "Hydra-Lurker Timing",
     "description": "Lurker ambushes deny pushes and set up economic third base."},
    {"id": "zvt_06", "matchup": "ZvT", "name": "Ultra-Bane Late Game",
     "description": "Ultralist with Baneling support crushes siege positions in late game."},
    {"id": "zvt_07", "matchup": "ZvT", "name": "Nydus Worm Drop",
     "description": "Nydus delivers units inside Terran main to disrupt production."},

    # ZvZ responses (7 strategies)
    {"id": "zvz_01", "matchup": "ZvZ", "name": "Pool-First Aggression",
     "description": "12 Pool into ling-flood to deny economic hatch before pool."},
    {"id": "zvz_02", "matchup": "ZvZ", "name": "Roach Warren Defence",
     "description": "Fast Roach Warren to hold early ling aggression then macro."},
    {"id": "zvz_03", "matchup": "ZvZ", "name": "Muta-Ling Mid Game",
     "description": "Mutalisks for map control, Zerglings trade efficiently mirror."},
    {"id": "zvz_04", "matchup": "ZvZ", "name": "Hydra Timing vs Muta",
     "description": "Hydralisk push targets Mutalisk heavy opponent with anti-air."},
    {"id": "zvz_05", "matchup": "ZvZ", "name": "Lurker Wall Defence",
     "description": "Lurker burrowed at natural choke holds aggression until macro lead."},
    {"id": "zvz_06", "matchup": "ZvZ", "name": "Infestor Blob",
     "description": "Infestors use Fungal Growth to clump and melt opposing Zerg army."},
    {"id": "zvz_07", "matchup": "ZvZ", "name": "Spire Skip Roach Max",
     "description": "Skip air tech, max Roach-Ravager to punish Mutalisk transition."},

    # ZvP builds (6 strategies)
    {"id": "zvp_01", "matchup": "ZvP", "name": "Roach-Ravager Timing",
     "description": "Ravager Corrosive Bile breaks Force Field allowing ling flood."},
    {"id": "zvp_02", "matchup": "ZvP", "name": "Ling-Bane-Hydra",
     "description": "Cost-efficient ground army that trades well against Immortal-Chargelot."},
    {"id": "zvp_03", "matchup": "ZvP", "name": "Muta-Ling Aggression",
     "description": "Mutalisks harass mineral lines forcing Protoss to go Stalker-heavy."},
    {"id": "zvp_04", "matchup": "ZvP", "name": "Lurker-Hydra",
     "description": "Lurker burrowed in key chokes controls Colossus-heavy Protoss."},
    {"id": "zvp_05", "matchup": "ZvP", "name": "Ultra-Infestor Combo",
     "description": "Infestor Neural Parasite targets Colossi; Ultralisks tank Chargelot."},
    {"id": "zvp_06", "matchup": "ZvP", "name": "Swarm-Host Nydus",
     "description": "Swarm Host locusts drain Protoss army near Nydus entry, then push."},
]

# ---------------------------------------------------------------------------
# Load embedding model
# ---------------------------------------------------------------------------
print("[Pinecone] Loading sentence-transformer model…")
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return L2-normalised embeddings for a list of text strings."""
    return model.encode(texts, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# Create / connect to Pinecone index
# ---------------------------------------------------------------------------
def init_index() -> pinecone.Index:
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)

    if INDEX_NAME not in pinecone.list_indexes():
        print(f"[Pinecone] Creating index '{INDEX_NAME}'…")
        pinecone.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
        )
        time.sleep(5)           # wait for index to be ready

    return pinecone.Index(INDEX_NAME)


# ---------------------------------------------------------------------------
# Upsert strategy vectors
# ---------------------------------------------------------------------------
def upsert_strategies(index: pinecone.Index) -> None:
    """Embed all 20 strategy descriptions and upsert into Pinecone."""
    texts    = [s["description"] for s in STRATEGIES]
    vectors  = embed_texts(texts)

    upsert_data = [
        (
            s["id"],
            vec,
            {"matchup": s["matchup"], "name": s["name"], "description": s["description"]},
        )
        for s, vec in zip(STRATEGIES, vectors)
    ]

    # Pinecone recommends batches of ≤ 100
    batch_size = 50
    for i in range(0, len(upsert_data), batch_size):
        index.upsert(vectors=upsert_data[i : i + batch_size])

    print(f"[Pinecone] Upserted {len(upsert_data)} strategy vectors.")


# ---------------------------------------------------------------------------
# Query: find similar strategies and recommend a counter
# ---------------------------------------------------------------------------
def query_similar_strategy(
    query_text: str,
    matchup_filter: str | None = None,
    top_k: int = TOP_K,
) -> list[dict]:
    """
    Find the nearest-neighbour strategies to the query description.
    Optionally filter by matchup (ZvT / ZvZ / ZvP).
    Returns a ranked list of strategy dicts with similarity scores.
    """
    index = pinecone.Index(INDEX_NAME)
    query_vec = embed_texts([query_text])[0]

    filter_dict = {"matchup": {"$eq": matchup_filter}} if matchup_filter else {}

    result = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict if filter_dict else None,
    )

    hits = []
    for match in result.matches:
        hits.append({
            "id":          match.id,
            "score":       round(match.score, 4),
            "matchup":     match.metadata.get("matchup"),
            "name":        match.metadata.get("name"),
            "description": match.metadata.get("description"),
        })
    return hits


def recommend_counter_strategy(opponent_strategy: str, matchup: str) -> None:
    """Print counter-strategy recommendations for a given opponent approach."""
    print(f"\n[Recommend] Opponent: '{opponent_strategy}' | Matchup: {matchup}")
    hits = query_similar_strategy(opponent_strategy, matchup_filter=matchup, top_k=3)
    print("Top counter recommendations:")
    for rank, hit in enumerate(hits, start=1):
        print(f"  {rank}. [{hit['score']:.4f}] {hit['name']} — {hit['description']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    index = init_index()
    upsert_strategies(index)

    # Demo queries
    recommend_counter_strategy(
        "Heavy Marine-Marauder bio ball with Medivacs", matchup="ZvT"
    )
    recommend_counter_strategy(
        "Mass Mutalisk into late-game Ling", matchup="ZvZ"
    )
    recommend_counter_strategy(
        "Immortal-Chargelot-Archon deathball", matchup="ZvP"
    )

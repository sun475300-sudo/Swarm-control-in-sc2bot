# Phase 410: LlamaIndex - SC2 Strategy RAG
# Retrieval Augmented Generation for SC2 strategy guides and match analysis

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    Settings,
    StorageContext,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb
from typing import List

# ============================================================
# Strategy Knowledge Base
# ============================================================

SC2_STRATEGY_DOCS = [
    Document(
        text="""
        ZvT Roach-Hydra Timing Attack:
        The roach-hydra push is a powerful mid-game timing attack against Terran bio.
        Build order: Pool first, gas x2, roach warren at 3:30, lair at 4:00.
        Attack timing: 9-10 minutes with 12 roaches + 8 hydralisks.
        Strengths: cost-efficient vs bio, good vs drops, strong map control.
        Weakness: vulnerable to tank-bio with good positioning, poor vs mech.
        When to attack: scout for fewer than 2 siege tanks, attack before turrets up.
        Counter: add corruptors if Terran goes air, get banelings vs mass bio.
        """,
        metadata={"matchup": "ZvT", "composition": "roach-hydra", "phase": "mid"},
    ),
    Document(
        text="""
        Counter to Mech Terran (ZvT):
        Mech Terran relies on tanks, hellions, and thors. Best counter is Zerg air+ground.
        Primary composition: Ultralisks + Brood Lords + Infestors.
        Key units: Brood Lords to siege tanks at range, Infestors for fungal growth.
        Alternative: mass Swarm Hosts to drain Terran resources.
        Build: double evo chamber for +2/+2, hive at 7:00, brood lord cavern.
        Timing: push before third base is secured, use burrowed roaches to flank.
        Positional play: force Terran to siege, then surround with flanking lings.
        Key tip: never run units into sieged tanks - use Infestor fungal to clump marines.
        """,
        metadata={"matchup": "ZvT", "composition": "brood-lord-infestor", "phase": "late"},
    ),
    Document(
        text="""
        ZvP Roach-Hydra-Ravager vs Protoss Stalker-Colossus:
        Ravagers are essential vs Protoss due to Force Field denial.
        Build: roach warren + ravager research, add hydralisk den at 5:30.
        Attack: 10-11 minutes with 8 roaches, 4 ravagers, 8 hydralisks.
        Use ravager bile to break force fields before engaging.
        Corruptors mandatory if Protoss gets Colossus (4+ Colossus = GG without corruptors).
        Transition: add Infestors for Disruptor shots, Vipers for late game.
        """,
        metadata={"matchup": "ZvP", "composition": "roach-ravager-hydra", "phase": "mid"},
    ),
    Document(
        text="""
        Early Game Build Orders - Zerg:
        12 Pool Fast Attack: hatch first at 17, pool at 12, aggressive zergling pressure.
        Safe Hatch-Gas-Pool: 17 hatch, 17 gas, 16 pool - standard economic opener.
        3 Hatch before Pool: 17 hatch, 19 hatch, 20 pool - greedy economy, requires scouting.
        Speedling expand: pool first, speed research, expand after 6 zerglings out.
        Always scout at 13 supply. Overlord scout is critical for detecting early aggression.
        vs Terran: look for proxy barracks, 1-1-1 builds, early reaper opening.
        vs Protoss: scout for 4-gate, stargate fast oracle, DT shrine.
        vs Zerg: check for pool timing, fast lair for mutalisk, 12 pool pressure.
        """,
        metadata={"matchup": "all", "phase": "early", "topic": "build-orders"},
    ),
    Document(
        text="""
        ZvZ Mutalisk Control and Micro:
        Mutalisks are the dominant unit in ZvZ mid-game. Key: mass before opponent.
        Build: 2-base lair at 3:30, spire at 4:30, first mutas at 6:00.
        Critical mass: 12+ mutalisks before engaging.
        Micro: stacking mutalisks maximizes bounce damage. Stack by clicking rally point.
        Counter to mutas: own mutalisks, queens (transfuse), or heavy spine crawler defense.
        Transition: roach-hydra vs muta-stacked play, or go brood lords after 20+ mutas.
        Map control: deny third base with mutas, force opponent to stay defensive.
        """,
        metadata={"matchup": "ZvZ", "composition": "mutalisk", "phase": "mid"},
    ),
    Document(
        text="""
        Mass Marines (Marine-Marauder-Medivac) Counter Strategies:
        Marine-Marauder-Medivac (MMM) is the most versatile Terran composition.
        Zerg counters: Banelings (splash), Infestors (fungal growth), Ultralisk.
        Key: banelings one-shot marines if not split. Fungal prevents splitting.
        Baneling bust vs bio: 20+ banelings with lings to surround.
        Mid-game: ling-bane-ravager with good fungals from Infestors.
        Late game: Ultralisks are armored and tanky vs bio without tanks.
        Never engage bio straight on - flank, surround, fungal first.
        Detect drops: use Overseers + spine crawlers at mineral lines.
        """,
        metadata={"matchup": "ZvT", "topic": "anti-bio", "phase": "mid"},
    ),
]

# ============================================================
# Index Construction with ChromaVectorStore
# ============================================================

def build_strategy_index() -> VectorStoreIndex:
    """Build a vector index from SC2 strategy documents using Chroma."""

    # Configure LLM and embedding model
    Settings.llm = Anthropic(model="claude-3-haiku-20240307", max_tokens=1024)
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # ChromaDB vector store
    chroma_client = chromadb.EphemeralClient()
    chroma_collection = chroma_client.get_or_create_collection("sc2_strategy")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Node parser: chunk strategy docs
    node_parser = SentenceSplitter(chunk_size=256, chunk_overlap=32)
    Settings.node_parser = node_parser

    # Build index
    index = VectorStoreIndex.from_documents(
        SC2_STRATEGY_DOCS,
        storage_context=storage_context,
        show_progress=True,
    )
    print(f"[LlamaIndex] Index built with {len(SC2_STRATEGY_DOCS)} strategy documents")
    return index

# ============================================================
# Query Engine
# ============================================================

def create_query_engine(index: VectorStoreIndex) -> RetrieverQueryEngine:
    retriever = VectorIndexRetriever(index=index, similarity_top_k=3)
    synthesizer = get_response_synthesizer(response_mode="compact")
    return RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
    )

def ask_strategy_question(query_engine: RetrieverQueryEngine, question: str) -> str:
    print(f"\n[RAG] Q: {question}")
    response = query_engine.query(question)
    print(f"[RAG] A: {response.response}")
    return response.response

# ============================================================
# Main
# ============================================================

def main():
    print("[LlamaIndex] Building SC2 strategy knowledge base...")
    index = build_strategy_index()
    qe    = create_query_engine(index)

    questions = [
        "What is the best counter to mech Terran?",
        "When should I attack with roach-hydra vs Terran?",
        "How do I counter mass marines?",
        "What is the best early game build order for Zerg?",
        "How do I control mutalisks in ZvZ?",
        "How to beat Protoss colossus?",
    ]

    for q in questions:
        ask_strategy_question(qe, q)

    print("\n[LlamaIndex] RAG pipeline complete.")

if __name__ == "__main__":
    main()

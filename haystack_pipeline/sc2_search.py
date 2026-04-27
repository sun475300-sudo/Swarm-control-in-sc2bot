# Phase 415: Haystack - SC2 Knowledge Retrieval Pipeline
# Deepset Haystack pipeline for SC2 strategy Q&A

from haystack import Document, Pipeline
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.readers import ExtractiveReader
from haystack.components.writers import DocumentWriter
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.preprocessors import DocumentSplitter
from typing import List

# ============================================================
# SC2 Strategy Knowledge Base
# ============================================================

SC2_STRATEGY_DOCS: List[Document] = [
    Document(
        content="""How to counter mass marines:
        Marine-Marauder-Medivac (MMM) is the most common Terran bio composition.
        The best Zerg counter is Banelings. Banelings deal splash damage and
        one-shot marines when clumped. Use Infestors for Fungal Growth to prevent
        splitting. Zerglings surround and flank bio without tank support.
        For late game, Ultralisks are armored and extremely tanky vs bio.
        Never engage bio head-on without Banelings or Fungal. Use flanking attacks.""",
        meta={"topic": "anti-bio", "matchup": "ZvT"},
    ),
    Document(
        content="""Best build order vs Protoss:
        Standard ZvP opener: 17 Hatchery, 17 Gas x2, 16 Pool, 21 Hatchery (natural).
        Build Roach Warren at 4:30. Research Ravager morph.
        Add Hydralisk Den at 6:00. Get +1/+1 attack/armor upgrades.
        Attack at 10-11 minutes with Roach-Ravager-Hydra army.
        Must have Corruptors if Protoss goes Colossus tech.
        Use Ravager bile shots to break Force Fields before engaging.""",
        meta={"topic": "build-order", "matchup": "ZvP"},
    ),
    Document(
        content="""Zerg vs Terran mech strategy:
        Mech Terran uses Tanks, Hellions, Thors, and Battlecruisers.
        Best counter: Brood Lords (out-range tanks), Infestors (Fungal to clump),
        Corruptors (vs air units and heavy armored ground).
        Swarm Hosts can drain Terran resources by forcing unit production.
        Vipers are essential late game: Abduct Thors and Battlecruisers.
        Key: never walk into sieged tanks. Use Infestor Fungal to reveal and clump.""",
        meta={"topic": "anti-mech", "matchup": "ZvT"},
    ),
    Document(
        content="""Zerg early game scouting guide:
        Send Overlord scout to enemy base at 13 supply.
        vs Terran: look for proxy barracks (2-3 rax proxy = aggressive), 1-1-1 build,
        early Reaper. If 2+ barracks = bio play incoming.
        vs Protoss: scout for 4-gate (4 gateways early), Stargate (fast Oracle/Phoenix),
        Dark Shrine (Dark Templar = detection required).
        vs Zerg: check for pool timing, fast Lair for Mutalisk, proxy Spawning Pool.
        React with appropriate defense: Spine Crawlers, Queens, Roach Warren.""",
        meta={"topic": "scouting", "matchup": "all"},
    ),
    Document(
        content="""ZvZ Mutalisk micro technique:
        Mutalisks are dominant in ZvZ because of the bounce damage mechanic.
        Stack Mutalisks by clicking a single rally point - they naturally stack.
        Stacked Mutalisks maximize the 3-bounce damage hitting the same target.
        12+ Mutalisks is the critical mass before engaging.
        Micro tip: run past Queen transfuse to deny healing.
        Counter: own Mutalisks, massed Queens (ground-based), or Spore Crawlers.
        Transition options: continue Muta-ling or switch to Roach-Hydra-Ravager.""",
        meta={"topic": "mutalisk", "matchup": "ZvZ"},
    ),
]

# ============================================================
# Document Store Setup
# ============================================================


def setup_document_store() -> InMemoryDocumentStore:
    store = InMemoryDocumentStore()

    # Indexing pipeline
    indexer = Pipeline()
    indexer.add_component(
        "splitter",
        DocumentSplitter(split_by="sentence", split_length=5, split_overlap=1),
    )
    indexer.add_component("writer", DocumentWriter(document_store=store))
    indexer.connect("splitter", "writer")

    indexer.run({"splitter": {"documents": SC2_STRATEGY_DOCS}})
    print(f"[Haystack] Document store: {store.count_documents()} chunks indexed")
    return store


# ============================================================
# QA Pipeline: BM25Retriever + ExtractiveReader
# ============================================================


def build_qa_pipeline(store: InMemoryDocumentStore) -> Pipeline:
    pipeline = Pipeline()
    pipeline.add_component(
        "retriever", InMemoryBM25Retriever(document_store=store, top_k=3)
    )
    pipeline.add_component(
        "reader", ExtractiveReader(model="deepset/roberta-base-squad2")
    )
    pipeline.connect("retriever.documents", "reader.documents")
    return pipeline


# ============================================================
# Ask Questions
# ============================================================


def ask_question(pipeline: Pipeline, question: str, top_k: int = 3) -> None:
    print(f"\n[Haystack] Q: {question}")
    result = pipeline.run(
        {
            "retriever": {"query": question},
            "reader": {"query": question, "top_k": top_k},
        }
    )

    answers = result.get("reader", {}).get("answers", [])
    if answers:
        best = answers[0]
        print(f"[Haystack] A: {best.data} (score: {best.score:.3f})")
        print(f"[Haystack] Source: ...{best.document.content[:80]}...")
    else:
        print("[Haystack] No answer found")


# ============================================================
# BM25-only Retrieval (no reader dependency)
# ============================================================


def keyword_search(store: InMemoryDocumentStore, query: str, top_k: int = 2) -> None:
    retriever = InMemoryBM25Retriever(document_store=store, top_k=top_k)
    results = retriever.run(query=query)
    docs = results.get("documents", [])
    print(f"\n[BM25] Query: '{query}'")
    for i, doc in enumerate(docs, 1):
        snippet = doc.content[:100].replace("\n", " ")
        print(f"  [{i}] {snippet}...")


# ============================================================
# Main
# ============================================================


def main():
    print("[Haystack] SC2 strategy knowledge pipeline starting...")
    store = setup_document_store()

    # BM25 keyword search (no model download needed)
    questions = [
        "How to counter mass marines?",
        "Best build order vs Protoss",
        "counter mech Terran",
        "mutalisk micro ZvZ",
        "scouting build Terran",
    ]

    for q in questions:
        keyword_search(store, q, top_k=2)

    print(
        "\n[Haystack] Pipeline ready. Use build_qa_pipeline() for extractive Q&A with reader."
    )
    print(
        "[Haystack] Note: ExtractiveReader requires deepset/roberta-base-squad2 model download."
    )


if __name__ == "__main__":
    main()

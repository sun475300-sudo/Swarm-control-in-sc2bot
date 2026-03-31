"""
Phase 441: Memgraph - SC2 Unit Relationship Graph Analysis
In-memory graph DB using gqlalchemy for Cypher queries.
"""

from gqlalchemy import Memgraph, Node, Relationship, Field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Connection
mg = Memgraph(host="127.0.0.1", port=7687)


# Node and Relationship models
class Unit(Node):
    name: str = Field(index=True, exists=True, unique=True, db=mg)
    race: str
    minerals: int
    gas: int
    supply: int


class Counters(Relationship, type="COUNTERS"):
    effectiveness: float  # 0.0 - 1.0


class BuildLeadsTo(Relationship, type="BUILD_LEADS_TO"):
    tech_level: int


def setup_schema():
    """Create indexes and constraints for SC2 graph."""
    mg.execute("CREATE INDEX ON :Unit(name);")
    mg.execute("CREATE CONSTRAINT ON (u:Unit) ASSERT u.name IS UNIQUE;")
    logger.info("Memgraph schema initialized.")


def insert_sample_units():
    """Insert sample SC2 Zerg units into the graph."""
    units = [
        {"name": "Zergling", "race": "Zerg", "minerals": 25, "gas": 0, "supply": 1},
        {"name": "Roach", "race": "Zerg", "minerals": 75, "gas": 25, "supply": 2},
        {"name": "Hydralisk", "race": "Zerg", "minerals": 100, "gas": 50, "supply": 2},
        {"name": "Mutalisk", "race": "Zerg", "minerals": 100, "gas": 100, "supply": 2},
        {"name": "Marine", "race": "Terran", "minerals": 50, "gas": 0, "supply": 1},
        {"name": "Marauder", "race": "Terran", "minerals": 100, "gas": 25, "supply": 2},
        {"name": "Thor", "race": "Terran", "minerals": 300, "gas": 200, "supply": 6},
    ]
    for u in units:
        mg.execute(
            "MERGE (u:Unit {name: $name}) SET u.race=$race, u.minerals=$minerals, "
            "u.gas=$gas, u.supply=$supply",
            u,
        )

    # Counter edges
    counters = [
        ("Marine", "Zergling", 0.85),
        ("Marauder", "Roach", 0.75),
        ("Thor", "Mutalisk", 0.90),
        ("Zergling", "Marine", 0.60),
        ("Mutalisk", "Marauder", 0.70),
    ]
    for src, dst, eff in counters:
        mg.execute(
            "MATCH (a:Unit {name:$src}), (b:Unit {name:$dst}) "
            "MERGE (a)-[:COUNTERS {effectiveness:$eff}]->(b)",
            {"src": src, "dst": dst, "eff": eff},
        )

    # Tech path edges
    tech = [("Zergling", "Baneling", 2), ("Roach", "Ravager", 3), ("Hydralisk", "Lurker", 3)]
    for src, dst, lvl in tech:
        mg.execute(
            "MERGE (a:Unit {name:$src}) MERGE (b:Unit {name:$dst}) "
            "MERGE (a)-[:BUILD_LEADS_TO {tech_level:$lvl}]->(b)",
            {"src": src, "dst": dst, "lvl": lvl},
        )
    logger.info("Sample units and relationships inserted.")


def find_best_counter(unit_name: str) -> list[dict]:
    """Find units that counter the given unit, ordered by effectiveness."""
    result = mg.execute_and_fetch(
        "MATCH (counter:Unit)-[r:COUNTERS]->(target:Unit {name:$name}) "
        "RETURN counter.name AS counter, r.effectiveness AS effectiveness "
        "ORDER BY r.effectiveness DESC LIMIT 5",
        {"name": unit_name},
    )
    counters = list(result)
    logger.info(f"Best counters for {unit_name}: {counters}")
    return counters


def optimal_tech_path(start_unit: str, max_depth: int = 4) -> list[dict]:
    """Find tech paths reachable from a starting unit."""
    result = mg.execute_and_fetch(
        "MATCH path=(start:Unit {name:$start})-[:BUILD_LEADS_TO*1..$depth]->(end:Unit) "
        "RETURN [n IN nodes(path) | n.name] AS path, length(path) AS steps "
        "ORDER BY steps",
        {"start": start_unit, "depth": max_depth},
    )
    paths = list(result)
    logger.info(f"Tech paths from {start_unit}: {paths}")
    return paths


def army_composition_graph(race: str) -> list[dict]:
    """Get full unit graph for a race including counter relationships."""
    result = mg.execute_and_fetch(
        "MATCH (a:Unit {race:$race})-[r:COUNTERS]->(b:Unit) "
        "RETURN a.name AS attacker, b.name AS target, r.effectiveness AS effectiveness, "
        "a.supply AS supply_cost ORDER BY a.name",
        {"race": race},
    )
    composition = list(result)
    return composition


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_schema()
    insert_sample_units()
    print("Counters for Roach:", find_best_counter("Roach"))
    print("Tech path from Zergling:", optimal_tech_path("Zergling"))
    print("Zerg army graph:", army_composition_graph("Zerg"))

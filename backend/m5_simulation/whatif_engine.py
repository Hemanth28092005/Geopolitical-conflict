from datetime import datetime, timezone
from backend.m5_simulation.graph_loader import get_graph
from backend.m5_simulation.cascade_engine import run_cascade
from backend.m5_simulation.shock_quantifier import quantify_shock
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import SimulationRun
from backend.core.logger import logger


def run_whatif(
    scenario: dict,
    save_to_db: bool = True
) -> dict:
    """
    Main what-if simulation entry point.

    scenario format:
    {
        "name": "Russia oil cutoff",
        "shocks": [
            {
                "from": "RUS",
                "to": "IND",
                "commodity": "CRUDE_OIL",
                "closure_pct": 50
            }
        ]
    }
    """
    name    = scenario.get("name", "Unnamed scenario")
    shocks  = scenario.get("shocks", [])

    if not shocks:
        return {"error": "No shocks defined in scenario"}

    logger.info(f"Running what-if simulation: '{name}' with {len(shocks)} shock(s)")

    # Step 1: Load graph
    G = get_graph()
    if G is None:
        return {"error": "Could not load trade graph"}

    # Step 2: Run BFS cascade
    cascade = run_cascade(G, shocks)
    if "error" in cascade:
        return cascade

    # Step 3: Quantify USD impact
    impact = quantify_shock(cascade, shocks)

    # Step 4: Build full result
    result = {
        "scenario":    name,
        "shocks":      shocks,
        "cascade":     cascade,
        "impact":      impact,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }

    # Step 5: Save to DB
    if save_to_db:
        db = SyncSessionLocal()
        try:
            db.add(SimulationRun(
                name=name,
                scenario={"shocks": shocks},
                results={
                    "node_impacts":  cascade["node_impacts"],
                    "edge_impacts":  cascade["edge_impacts"],
                    "impact_summary": impact,
                },
                affected_countries=cascade["affected_count"],
                affected_commodities=len(set(
                    s.get("commodity", "ALL") for s in shocks
                )),
                total_impact_usd=impact["total_impact_usd"]
            ))
            db.commit()
            logger.info(f"Simulation '{name}' saved to DB")
        except Exception as e:
            logger.error(f"Failed to save simulation: {e}")
            db.rollback()
        finally:
            db.close()

    return result


def print_simulation_report(result: dict):
    """Pretty print simulation results to terminal."""
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    impact  = result["impact"]
    cascade = result["cascade"]

    print(f"\n{'='*60}")
    print(f"SIMULATION: {result['scenario']}")
    print(f"{'='*60}")

    print(f"\nSHOCKS APPLIED:")
    for s in result["shocks"]:
        print(f"  {s['from']}→{s['to']} {s['commodity']} — {s['closure_pct']}% closure")

    print(f"\nIMPACT SUMMARY:")
    print(f"  Direct impact:  ${impact['direct_impact_usd']/1e9:.1f}B")
    print(f"  Cascade impact: ${impact['cascade_impact_usd']/1e9:.1f}B")
    print(f"  Total impact:   ${impact['total_impact_usd']/1e9:.1f}B")

    print(f"\nTOP AFFECTED COUNTRIES:")
    for c in impact["top_affected_countries"]:
        print(f"  {c['country']:<8} ${c['impact_usd']/1e9:.1f}B")

    print(f"\nNODE IMPACT SCORES (0–100):")
    sorted_nodes = sorted(
        cascade["node_impacts"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    for node, score in sorted_nodes:
        bar = "█" * int(score / 5)
        print(f"  {node:<8} {score:>5.1f}  {bar}")

    print(f"\nCASCADE DEPTH: {len(cascade['edge_impacts'])} edges affected")
    print(f"{'='*60}\n")
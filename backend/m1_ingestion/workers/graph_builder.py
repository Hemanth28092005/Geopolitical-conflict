import json
import networkx as nx
import redis as redis_client
from backend.m1_ingestion.celery_app import celery_app
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import TradeRoute, Country, TradeEvent
from backend.core.config import get_settings
from backend.core.logger import logger

settings = get_settings()


def build_graph_from_db(db) -> nx.DiGraph:
    """Build directed weighted trade graph from DB trade routes."""
    G = nx.DiGraph()

    countries = db.query(Country).filter(Country.is_active == True).all()
    for c in countries:
        G.add_node(
            c.iso_code,
            name=c.name,
            region=c.region,
            gdp=c.gdp_usd or 0
        )

    routes = db.query(TradeRoute).all()
    for r in routes:
        from_iso  = r.from_country.iso_code
        to_iso    = r.to_country.iso_code
        commodity = r.commodity.code if r.commodity else "UNKNOWN"
        weight    = min((r.annual_value_usd or 0) / 1e12, 1.0)

        if G.has_edge(from_iso, to_iso):
            G[from_iso][to_iso]["weight"] += weight
            G[from_iso][to_iso]["commodities"].append(commodity)
            G[from_iso][to_iso]["annual_value_usd"] += (r.annual_value_usd or 0)
        else:
            G.add_edge(
                from_iso, to_iso,
                weight=weight,
                annual_value_usd=r.annual_value_usd or 0,
                commodities=[commodity],
                is_critical=r.is_critical or False
            )

    return G


def get_pending_article_urls(db, limit: int = 50) -> list[dict]:
    """
    Pull recent GDELT trade events that have source URLs.
    These will be queued for M3 sentiment scoring.
    """
    recent_events = (
        db.query(TradeEvent)
        .filter(TradeEvent.source_url != None)
        .order_by(TradeEvent.time.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "url": e.source_url,
            "country_id": str(e.country_id),
            "event_time": e.time.isoformat()
        }
        for e in recent_events
        if e.source_url
    ]


@celery_app.task(name="backend.m1_ingestion.workers.graph_builder.build_trade_graph")
def build_trade_graph():
    """
    Build trade graph and cache in Redis.
    Also pushes pending article URLs to Redis queue for M3 to consume.
    """
    logger.info("Building trade graph...")
    db = SyncSessionLocal()

    try:
        r = redis_client.from_url(settings.redis_url)

        # 1. Build and cache the trade graph (used by M5 simulation)
        G = build_graph_from_db(db)
        graph_data = nx.node_link_data(G)
        r.setex("trade_graph", 7200, json.dumps(graph_data))

        # 2. Push article URLs to Redis list for M3 to consume
        pending_urls = get_pending_article_urls(db, limit=50)
        if pending_urls:
            # Clear old queue, push fresh batch
            r.delete("pending_articles")
            for item in pending_urls:
                r.rpush("pending_articles", json.dumps(item))
            logger.info(f"Pushed {len(pending_urls)} article URLs to Redis for M3")

        stats = {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "pending_articles": len(pending_urls),
            "status": "ok"
        }

        logger.info(f"Graph built — {stats['nodes']} nodes, {stats['edges']} edges, {stats['pending_articles']} articles queued")
        return stats

    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        return {"status": "error", "reason": str(e)}

    finally:
        db.close()
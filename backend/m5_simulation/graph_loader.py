import json
import networkx as nx
import redis as redis_client
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import TradeRoute, Country, Commodity
from backend.core.config import get_settings
from backend.core.logger import logger

settings = get_settings()


def load_graph_from_redis() -> nx.DiGraph | None:
    """Load cached trade graph from Redis."""
    try:
        r = redis_client.from_url(settings.redis_url)
        raw = r.get("trade_graph")
        if not raw:
            logger.warning("No trade graph in Redis — rebuild needed")
            return None
        data = json.loads(raw)
        G = nx.node_link_graph(data)
        logger.info(f"Graph loaded from Redis: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Graph load failed: {e}")
        return None


def load_graph_from_db() -> nx.DiGraph:
    """
    Fallback — build graph directly from DB if Redis cache is empty.
    """
    logger.info("Building graph from DB (Redis cache miss)...")
    db = SyncSessionLocal()

    try:
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
            value     = r.annual_value_usd or 0
            weight    = min(value / 1e12, 1.0)

            if G.has_edge(from_iso, to_iso):
                G[from_iso][to_iso]["weight"]           += weight
                G[from_iso][to_iso]["annual_value_usd"] += value
                G[from_iso][to_iso]["commodities"].append(commodity)
            else:
                G.add_edge(
                    from_iso, to_iso,
                    weight=weight,
                    annual_value_usd=value,
                    commodities=[commodity],
                    is_critical=r.is_critical or False
                )

        logger.info(f"Graph built from DB: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    finally:
        db.close()


def get_graph() -> nx.DiGraph:
    """Get trade graph — Redis first, DB fallback."""
    G = load_graph_from_redis()
    if G is None or G.number_of_nodes() == 0:
        G = load_graph_from_db()
    return G


def get_route_details() -> dict:
    """
    Return a lookup dict of all trade routes keyed by (from_iso, to_iso, commodity).
    Used by the shock quantifier.
    """
    db = SyncSessionLocal()
    try:
        routes = db.query(TradeRoute).all()
        result = {}
        for r in routes:
            key = (
                r.from_country.iso_code,
                r.to_country.iso_code,
                r.commodity.code if r.commodity else "UNKNOWN"
            )
            result[key] = {
                "id":               str(r.id),
                "annual_value_usd": r.annual_value_usd or 0,
                "is_critical":      r.is_critical or False,
            }
        return result
    finally:
        db.close()
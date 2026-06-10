from backend.m5_simulation.graph_loader import get_route_details
from backend.core.logger import logger


def quantify_shock(
    cascade_result: dict,
    shocked_edges:  list[dict]
) -> dict:
    """
    Convert cascade impact scores into USD estimates
    and per-commodity breakdowns.
    """
    route_details  = get_route_details()
    node_impacts   = cascade_result.get("node_impacts", {})
    edge_impacts   = cascade_result.get("edge_impacts", [])

    # Calculate direct USD impact from shocked edges
    direct_impact_usd   = 0.0
    commodity_impacts   = {}
    country_impacts_usd = {}

    for shock in shocked_edges:
        from_iso     = shock["from"]
        to_iso       = shock["to"]
        commodity    = shock.get("commodity", "ALL")
        closure_pct  = shock.get("closure_pct", 50) / 100.0

        key = (from_iso, to_iso, commodity)
        route = route_details.get(key)

        if route:
            impact_usd = route["annual_value_usd"] * closure_pct
            direct_impact_usd += impact_usd

            # Per commodity
            commodity_impacts[commodity] = (
                commodity_impacts.get(commodity, 0) + impact_usd
            )

            # Per country
            country_impacts_usd[to_iso] = (
                country_impacts_usd.get(to_iso, 0) + impact_usd
            )

    # Cascade USD impact — estimate from node impact scores
    cascade_impact_usd = 0.0
    for edge in edge_impacts:
        if edge.get("is_direct"):
            continue
        from_iso  = edge["from"]
        to_iso    = edge["to"]
        shock_pct = edge["closure_pct"] / 100.0

        # Look up any route between these nodes
        for (f, t, c), details in route_details.items():
            if f == from_iso and t == to_iso:
                est_impact = details["annual_value_usd"] * shock_pct * 0.3
                cascade_impact_usd += est_impact
                country_impacts_usd[to_iso] = (
                    country_impacts_usd.get(to_iso, 0) + est_impact
                )

    total_impact_usd = direct_impact_usd + cascade_impact_usd

    # Sort countries by impact
    top_affected = sorted(
        [
            {"country": iso, "impact_usd": round(usd, 0)}
            for iso, usd in country_impacts_usd.items()
        ],
        key=lambda x: x["impact_usd"],
        reverse=True
    )

    return {
        "direct_impact_usd":   round(direct_impact_usd, 0),
        "cascade_impact_usd":  round(cascade_impact_usd, 0),
        "total_impact_usd":    round(total_impact_usd, 0),
        "commodity_impacts":   commodity_impacts,
        "top_affected_countries": top_affected[:10],
    }
# backend/models/model_graph.py
# UPGRADE 2 — Connected Model Propagation Engine
from collections import deque

DEPENDENCIES = {
    "sales_volume": ["revenue", "market_share", "gross_profit"],
    "revenue": ["gross_profit", "net_profit", "profit_margin"],
    "gross_profit": ["net_profit", "ebitda"],
    "net_profit": ["eps", "roe"],
    "average_price": ["revenue", "gross_profit"],
    "cost_of_goods_percent": ["gross_profit", "net_profit"],
    "operating_expenses": ["net_profit", "ebitda"],
    "tax_rate": ["net_profit", "eps"],
}


class ModelGraph:
    """BFS-based dependency graph that propagates driver changes through all connected metrics."""

    def __init__(self):
        self.dependencies = DEPENDENCIES

    def _calculate_all(self, drivers: dict) -> dict:
        """Full metric calculation from raw drivers."""
        sales_volume = drivers.get("sales_volume", 0)
        average_price = drivers.get("average_price", 0)
        cost_pct = drivers.get("cost_of_goods_percent", 0)
        opex = drivers.get("operating_expenses", 0)
        tax_rate = drivers.get("tax_rate", 0)
        total_market = drivers.get("total_market_size", 1)
        shares_outstanding = drivers.get("shares_outstanding", 1000000)

        revenue = (sales_volume * average_price) / 1e7
        gross_profit = revenue * (1 - cost_pct / 100)
        ebitda = gross_profit - opex
        net_profit = gross_profit - opex - (gross_profit * tax_rate / 100)
        market_share = (sales_volume / total_market) * 100 if total_market else 0
        profit_margin = (net_profit / revenue) * 100 if revenue else 0
        eps = (net_profit * 1e7) / shares_outstanding if shares_outstanding else 0
        roe = (net_profit / max(revenue * 0.3, 1)) * 100

        return {
            "revenue": round(revenue, 2),
            "gross_profit": round(gross_profit, 2),
            "net_profit": round(net_profit, 2),
            "ebitda": round(ebitda, 2),
            "market_share": round(market_share, 4),
            "profit_margin": round(profit_margin, 2),
            "eps": round(eps, 2),
            "roe": round(roe, 2),
        }

    def propagate(self, changed_driver: str, new_value: float, current_drivers: dict) -> dict:
        """
        BFS traversal of dependency graph.
        Returns updated metrics and the propagation path.
        """
        # Calculate baseline with old drivers
        old_metrics = self._calculate_all(current_drivers)

        # Apply change
        updated_drivers = current_drivers.copy()
        updated_drivers[changed_driver] = new_value
        new_metrics = self._calculate_all(updated_drivers)

        # BFS to find all affected metrics
        visited = set()
        queue = deque()
        path_segments = []

        # Seed the queue with direct dependents of the changed driver
        if changed_driver in self.dependencies:
            for dep in self.dependencies[changed_driver]:
                queue.append((changed_driver, dep))
                visited.add(dep)

        while queue:
            parent, current = queue.popleft()
            path_segments.append(f"{parent} → {current}")

            # Traverse deeper
            if current in self.dependencies:
                for next_dep in self.dependencies[current]:
                    if next_dep not in visited:
                        visited.add(next_dep)
                        queue.append((current, next_dep))

        # Build updated_metrics dict showing changes
        updated_metrics = {}
        changes = []
        for metric_name in visited:
            old_val = old_metrics.get(metric_name, 0)
            new_val = new_metrics.get(metric_name, 0)
            diff = new_val - old_val
            pct_change = (diff / old_val * 100) if old_val != 0 else 0

            updated_metrics[metric_name] = {
                "old_value": old_val,
                "new_value": new_val,
                "absolute_change": round(diff, 4),
                "percent_change": round(pct_change, 2),
            }
            changes.append({
                "metric": metric_name,
                "from": old_val,
                "to": new_val,
                "change_pct": round(pct_change, 2),
            })

        # Build clean propagation path
        full_path = self._build_propagation_path(changed_driver)

        return {
            "updated_metrics": updated_metrics,
            "all_metrics": new_metrics,
            "propagation_path": full_path,
            "cascade_count": len(visited),
            "changes": changes,
            "driver_changed": changed_driver,
            "old_value": current_drivers.get(changed_driver, 0),
            "new_value": new_value,
        }

    def _build_propagation_path(self, start: str) -> list:
        """Build a readable list of propagation path strings."""
        paths = []
        visited = set()
        queue = deque([(start, [start])])

        while queue:
            node, path = queue.popleft()
            if node in self.dependencies:
                for dep in self.dependencies[node]:
                    if dep not in visited:
                        visited.add(dep)
                        new_path = path + [dep]
                        paths.append(" → ".join(new_path))
                        queue.append((dep, new_path))

        return paths

    def impact_score(self, changed_driver: str) -> dict:
        """Return how many metrics are affected and which are most sensitive."""
        if changed_driver not in self.dependencies:
            return {"affected_count": 0, "affected_metrics": [], "sensitivity_rank": []}

        # BFS to count all reachable nodes
        visited = set()
        queue = deque([changed_driver])
        while queue:
            node = queue.popleft()
            if node in self.dependencies:
                for dep in self.dependencies[node]:
                    if dep not in visited:
                        visited.add(dep)
                        queue.append(dep)

        # Rank by depth (deeper = less direct impact)
        sensitivity_rank = []
        queue2 = deque([(changed_driver, 0)])
        visited2 = set()
        while queue2:
            node, depth = queue2.popleft()
            if node in self.dependencies:
                for dep in self.dependencies[node]:
                    if dep not in visited2:
                        visited2.add(dep)
                        sensitivity_rank.append({
                            "metric": dep,
                            "depth": depth + 1,
                            "impact_level": "High" if depth == 0 else "Medium" if depth == 1 else "Low",
                        })
                        queue2.append((dep, depth + 1))

        # Sort by depth (most affected first)
        sensitivity_rank.sort(key=lambda x: x["depth"])

        return {
            "affected_count": len(visited),
            "affected_metrics": list(visited),
            "sensitivity_rank": sensitivity_rank,
        }

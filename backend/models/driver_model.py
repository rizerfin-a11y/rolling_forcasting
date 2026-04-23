# backend/models/driver_model.py

class DriverModel:
    def calculate(self, drivers: dict) -> dict:
        sales_volume = drivers.get("sales_volume", 0)
        average_price = drivers.get("average_price", 0)
        cost_of_goods_percent = drivers.get("cost_of_goods_percent", 0)
        operating_expenses = drivers.get("operating_expenses", 0)
        tax_rate = drivers.get("tax_rate", 0)
        total_market_size = drivers.get("total_market_size", 1)

        revenue = (sales_volume * average_price) / 10000000  # in crores
        gross_profit = revenue * (1 - cost_of_goods_percent / 100)
        net_profit = gross_profit - operating_expenses - (gross_profit * tax_rate / 100)
        market_share = (sales_volume / total_market_size) * 100 if total_market_size else 0
        profit_margin = (net_profit / revenue) * 100 if revenue else 0

        return {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "market_share": market_share,
            "profit_margin": profit_margin
        }

    def sensitivity(self, drivers: dict, variable: str, target_metric: str) -> list:
        results = []
        base_val = drivers.get(variable, 0)
        for pct in [-30, -20, -10, 0, 10, 20, 30]:
            test_drivers = drivers.copy()
            test_drivers[variable] = base_val * (1 + pct / 100.0)
            res = self.calculate(test_drivers)
            results.append({
                "pct_change": pct,
                "variable_value": test_drivers[variable],
                "target_metric_value": res.get(target_metric, 0)
            })
        return results

    def goal_seek(self, drivers: dict, target_metric: str, target_value: float, variable_driver: str) -> dict:
        low = 0.0
        is_pct = "percent" in variable_driver or "rate" in variable_driver
        high = 100.0 if is_pct else 1e9

        best_val = drivers.get(variable_driver, 0)
        for _ in range(100):
            mid = (low + high) / 2
            test_d = drivers.copy()
            test_d[variable_driver] = mid
            res = self.calculate(test_d)
            current_target = res.get(target_metric, 0)
            
            # test correlation
            test_up = test_d.copy()
            test_up[variable_driver] = mid * 1.01
            res_up = self.calculate(test_up).get(target_metric, 0)
            positive_correlation = res_up >= current_target

            diff = current_target - target_value
            if abs(diff) < 1e-4:
                best_val = mid
                break
                
            if positive_correlation:
                if diff > 0: high = mid
                else: low = mid
            else:
                if diff > 0: low = mid
                else: high = mid
                
            best_val = mid
            
        final_res = self.calculate({**drivers, variable_driver: best_val})
        return {
            "required_value": round(best_val, 4),
            "achieved_target": round(final_res.get(target_metric, 0), 4)
        }

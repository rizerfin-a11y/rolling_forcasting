# backend/data_processor.py
# Complete working version
# Antigravity may have edited this — use this as the definitive version

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


class FinancialDataProcessor:
    """
    Converts raw financial data into AI-trainable knowledge chunks.
    Works for: annual reports, Tally exports, bank statements, SMB transactions
    """

    def __init__(self, company_name: str, currency: str = "INR"):
        self.company_name = company_name
        self.currency = currency
        self.chunks = []

    # ── Load Tata Motors annual data (from PDF you uploaded) ─────────────────
    def load_tata_annual_data(self) -> pd.DataFrame:
        """Load Tata Motors 8-year financial history exactly from the uploaded PDF."""
        data = {
            'fiscal_year': [
                '2015-16','2016-17','2017-18','2018-19',
                '2019-20','2020-21','2021-22','2022-23'
            ],
            'consolidated_turnover': [
                28107844, 27524666, 29629823, 30490371,
                26404112, 25243794, 28150725, 35060015
            ],
            'standalone_turnover': [
                4877959, 5007925, 6118229, 7175742,
                4531122, 4787443, 4792359, 6657827
            ],
            'jlr_revenue_gbp_mn': [
                22208, 24339, 25786, 24214,
                22984, 19731, 18320, 22809
            ],
            'consolidated_pbt': [
                1398087, 931479, 1115503, -3137115,
                -1057998, -1047428, -700341, 305755
            ],
            'standalone_pbt': [
                15039, -242077, -94692, 239893,
                -712734, -231257, -124754, 125480
            ],
            'jlr_pbt_gbp_mn': [
                1557, 1573, 1512, -3629,
                -422, -861, -455, 97
            ],
            'consolidated_pat': [
                1102375, 745436, 898891, -2882623,
                -1207085, -1345139, -1144147, 241429
            ],
            'standalone_pat': [
                23423, -247999, -103485, 202060,
                -728963, -239544, -139086, 272813
            ],
            'jlr_pat_gbp_mn': [
                1312, 1242, 1114, -3321,
                -469, -1100, -822, -60
            ],
            'consolidated_tax': [
                287260, 325123, 434193, -243745,
                39525, 254186, 423129, 70406
            ],
            'standalone_tax': [
                8384, 5922, 8793, 37833,
                16229, 8287, 14332, -147333
            ],
            'consolidated_depreciation': [
                1701418, 1790499, 2155359, 2359063,
                2142543, 2354671, 2483569, 2486036
            ],
            'standalone_depreciation': [
                245375, 296939, 310189, 309864,
                337529, 368161, 176057, 176686
            ],
            'jlr_depreciation_gbp_mn': [
                1418, 1656, 2075, 2164,
                1910, 1976, 1944, 2042
            ],
        }
        df = pd.DataFrame(data)

        # Derived columns
        df['consolidated_turnover_cr'] = df['consolidated_turnover'] / 100
        df['standalone_turnover_cr']   = df['standalone_turnover'] / 100
        df['consolidated_pbt_cr']      = df['consolidated_pbt'] / 100
        df['standalone_pbt_cr']        = df['standalone_pbt'] / 100
        df['consolidated_pat_cr']      = df['consolidated_pat'] / 100
        df['standalone_pat_cr']        = df['standalone_pat'] / 100
        df['consolidated_net_margin']  = (
            df['consolidated_pat'] / df['consolidated_turnover'] * 100
        ).round(2)
        df['standalone_net_margin']    = (
            df['standalone_pat'] / df['standalone_turnover'] * 100
        ).round(2)
        df['dep_as_pct_revenue']       = (
            df['consolidated_depreciation'] / df['consolidated_turnover'] * 100
        ).round(2)
        df['consolidated_rev_yoy']     = df['consolidated_turnover'].pct_change() * 100
        df['standalone_rev_yoy']       = df['standalone_turnover'].pct_change() * 100

        return df

    # ── Create knowledge chunks ───────────────────────────────────────────────
    def create_knowledge_chunks(self, df: pd.DataFrame) -> list:
        """Convert financial data into natural language chunks for AI training."""
        chunks = []

        # Chunk Type 1: Yearly summaries
        for _, row in df.iterrows():
            fy  = row['fiscal_year']
            cr  = row['consolidated_turnover_cr']
            sr  = row['standalone_turnover_cr']
            jr  = row['jlr_revenue_gbp_mn']
            pb  = row['consolidated_pbt_cr']
            pa  = row['consolidated_pat_cr']
            mg  = row['consolidated_net_margin']
            dp  = row['dep_as_pct_revenue']

            status = "PROFIT" if pa > 0 else "LOSS"

            text = f"""Tata Motors FY {fy} Annual Financial Summary:
- Consolidated Revenue (Turnover incl. Other Income): Rs {cr:,.0f} Crores (Rs {row['consolidated_turnover']:,} Lakhs)
- Standalone Revenue (India only): Rs {sr:,.0f} Crores
- JLR Revenue: GBP {jr:,} Million
- Consolidated Profit Before Tax (PBT): Rs {pb:,.0f} Crores
- Consolidated Profit After Tax (PAT / Net Profit): Rs {pa:,.0f} Crores [{status}]
- Standalone PAT: Rs {row['standalone_pat_cr']:,.0f} Crores
- JLR PBT: GBP {row['jlr_pbt_gbp_mn']:,} Million
- Net Profit Margin (Consolidated): {mg:.2f}%
- Depreciation and Amortisation: Rs {row['consolidated_depreciation']/100:,.0f} Crores ({dp:.1f}% of revenue)
- Consolidated Tax: Rs {row['consolidated_tax']/100:,.0f} Crores"""

            chunks.append({
                "id": f"tata_fy_{fy.replace('-','_')}",
                "type": "yearly_summary",
                "fiscal_year": fy,
                "text": text.strip(),
                "metadata": {
                    "company": "Tata Motors",
                    "period": fy,
                    "data_type": "annual_summary",
                    "is_profitable": bool(pa > 0),
                    "revenue_cr": float(cr),
                    "pat_cr": float(pa),
                }
            })

        # Chunk Type 2: YoY comparisons
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            rev_ch = curr['consolidated_turnover_cr'] - prev['consolidated_turnover_cr']
            rev_pct = curr['consolidated_rev_yoy']
            direction = "increased" if rev_ch > 0 else "decreased"

            text = f"""Tata Motors Revenue Comparison FY {prev['fiscal_year']} vs FY {curr['fiscal_year']}:
- Revenue {direction} by Rs {abs(rev_ch):,.0f} Crores ({rev_pct:+.1f}%)
- Previous year ({prev['fiscal_year']}): Rs {prev['consolidated_turnover_cr']:,.0f} Crores
- Current year ({curr['fiscal_year']}): Rs {curr['consolidated_turnover_cr']:,.0f} Crores
- PAT change: from Rs {prev['consolidated_pat_cr']:,.0f} Cr to Rs {curr['consolidated_pat_cr']:,.0f} Cr
- JLR revenue: GBP {prev['jlr_revenue_gbp_mn']:,}Mn → GBP {curr['jlr_revenue_gbp_mn']:,}Mn"""

            chunks.append({
                "id": f"tata_yoy_{prev['fiscal_year'].replace('-','_')}_{curr['fiscal_year'].replace('-','_')}",
                "type": "yoy_comparison",
                "fiscal_year": curr['fiscal_year'],
                "text": text.strip(),
                "metadata": {
                    "company": "Tata Motors",
                    "period": curr['fiscal_year'],
                    "data_type": "yoy_comparison",
                    "revenue_growth_pct": float(round(rev_pct, 2)) if not np.isnan(rev_pct) else 0,
                }
            })

        # Chunk Type 3: Revenue trend
        rev_vals = df['consolidated_turnover_cr'].tolist()
        max_rev_idx = rev_vals.index(max(rev_vals))
        min_rev_idx = rev_vals.index(min(rev_vals))

        trend_text = "Tata Motors 8-Year Consolidated Revenue Trend:\n"
        for i, row in df.iterrows():
            trend_text += f"- FY {row['fiscal_year']}: Rs {row['consolidated_turnover_cr']:,.0f} Crores"
            if not np.isnan(row['consolidated_rev_yoy']):
                trend_text += f" ({row['consolidated_rev_yoy']:+.1f}% YoY)"
            trend_text += "\n"
        trend_text += f"\nPeak revenue: FY {df.iloc[max_rev_idx]['fiscal_year']} at Rs {max(rev_vals):,.0f} Crores\n"
        trend_text += f"Lowest revenue: FY {df.iloc[min_rev_idx]['fiscal_year']} at Rs {min(rev_vals):,.0f} Crores\n"
        trend_text += f"8-year average: Rs {sum(rev_vals)/len(rev_vals):,.0f} Crores\n"
        trend_text += f"Total growth (2015-16 to 2022-23): {((rev_vals[-1]-rev_vals[0])/rev_vals[0]*100):+.1f}%"

        chunks.append({
            "id": "tata_revenue_trend_8yr",
            "type": "trend",
            "text": trend_text.strip(),
            "metadata": {"company": "Tata Motors", "data_type": "revenue_trend"}
        })

        # Chunk Type 4: Profit/Loss history
        pat_vals = df['consolidated_pat_cr'].tolist()
        loss_years = [df.iloc[i]['fiscal_year'] for i in range(len(df)) if pat_vals[i] < 0]
        profit_years = [df.iloc[i]['fiscal_year'] for i in range(len(df)) if pat_vals[i] >= 0]

        profit_text = "Tata Motors Profit and Loss History (Consolidated PAT):\n"
        for i, row in df.iterrows():
            status = "PROFIT" if pat_vals[i] >= 0 else "LOSS"
            profit_text += f"- FY {row['fiscal_year']}: Rs {pat_vals[i]:,.0f} Crores [{status}]\n"
        profit_text += f"\nProfit years: {', '.join(profit_years)}\n"
        profit_text += f"Loss years: {', '.join(loss_years)}\n"
        profit_text += f"Biggest single-year loss: Rs {min(pat_vals):,.0f} Crores in FY {df.iloc[pat_vals.index(min(pat_vals))]['fiscal_year']}\n"
        profit_text += f"Tata Motors returned to profitability in FY 2022-23 after {len(loss_years)} consecutive loss years"

        chunks.append({
            "id": "tata_profit_loss_history",
            "type": "trend",
            "text": profit_text.strip(),
            "metadata": {"company": "Tata Motors", "data_type": "profit_trend"}
        })

        # Chunk Type 5: Margin analysis
        margins = df['consolidated_net_margin'].tolist()
        margin_text = "Tata Motors Net Profit Margin History (Consolidated %):\n"
        for i, row in df.iterrows():
            margin_text += f"- FY {row['fiscal_year']}: {margins[i]:+.2f}%\n"
        margin_text += f"\nBest margin: FY {df.iloc[margins.index(max(margins))]['fiscal_year']} at {max(margins):.2f}%\n"
        margin_text += f"Worst margin: FY {df.iloc[margins.index(min(margins))]['fiscal_year']} at {min(margins):.2f}%\n"
        margin_text += "Note: Negative margins from 2018-19 to 2021-22 driven by JLR writedowns and COVID"

        chunks.append({
            "id": "tata_margin_history",
            "type": "ratio",
            "text": margin_text.strip(),
            "metadata": {"company": "Tata Motors", "data_type": "margin_trend"}
        })

        # Chunk Type 6: Business context
        chunks.append({
            "id": "tata_business_context",
            "type": "context",
            "text": """Tata Motors Business Structure and Key Facts:
- TWO main segments: Standalone India operations + JLR (Jaguar Land Rover UK)
- India standalone: Commercial vehicles (trucks, buses) + EVs (Nexon EV, Punch EV, Tiago EV)
- JLR: Luxury brand (Jaguar + Land Rover), reports in GBP, headquartered in UK
- JLR is the LARGER revenue contributor in absolute terms
- 4-year loss period (2018-2022) caused by: JLR impairment writedown (Rs 27,800 Cr in FY19), Brexit, COVID-19, chip shortage
- FY 2022-23: First consolidated profit in 5 years — JLR recovered, India EV sales grew
- Standalone data from FY 2021-22 excludes PV business (transferred to Tata Motors Passenger Vehicles Ltd)
- Data source: Tata Motors Financial Statistics History (official company document)
- All consolidated figures: Ind AS accounting standard. JLR: IFRS standard.""".strip(),
            "metadata": {"company": "Tata Motors", "data_type": "business_context"}
        })

        # Chunk Type 7: Loss explanation
        chunks.append({
            "id": "tata_loss_period_explanation",
            "type": "context",
            "text": """Why Tata Motors Had Losses from FY 2018-19 to FY 2021-22:
1. FY 2018-19 (Rs -28,826 Cr loss): JLR booked Rs 27,800 Cr goodwill impairment + diesel car demand fell in Europe + Brexit uncertainty hit JLR sales
2. FY 2019-20 (Rs -12,071 Cr loss): COVID-19 started in Q4 FY20, JLR sales halted, raw material costs spiked
3. FY 2020-21 (Rs -13,451 Cr loss): Full COVID year, global semiconductor chip shortage began, JLR factories stopped production for months
4. FY 2021-22 (Rs -11,441 Cr loss): Chip shortage continued, JLR had 168,000+ undelivered cars due to chip supply, high commodity prices
5. FY 2022-23 (Rs +2,414 Cr PROFIT): Chip supply normalised, JLR order book cleared, India standalone profitable (Rs +2,728 Cr), EV growth""".strip(),
            "metadata": {"company": "Tata Motors", "data_type": "loss_explanation"}
        })

        # Chunk Type 8: JLR analysis
        chunks.append({
            "id": "tata_jlr_analysis",
            "type": "context",
            "text": f"""Tata Motors JLR (Jaguar Land Rover) Revenue Analysis:
- FY 2015-16: GBP 22,208 Mn
- FY 2016-17: GBP 24,339 Mn (peak — best JLR year)
- FY 2017-18: GBP 25,786 Mn (highest ever JLR revenue)
- FY 2018-19: GBP 24,214 Mn (fell due to diesel ban fears in Europe)
- FY 2019-20: GBP 22,984 Mn (COVID impact Q4)
- FY 2020-21: GBP 19,731 Mn (worst COVID year for JLR)
- FY 2021-22: GBP 18,320 Mn (lowest — chip shortage halted production)
- FY 2022-23: GBP 22,809 Mn (strong recovery, back to 2016 levels)
JLR contributes ~70-75% of Tata Motors consolidated revenue when converted to INR.
JLR profit/loss directly determines whether Tata Motors consolidated makes profit or loss.""".strip(),
            "metadata": {"company": "Tata Motors", "data_type": "jlr_analysis"}
        })

        self.chunks = chunks
        return chunks

    # ── Required methods ──────────────────────────────────────────────────────
    def save_chunks_as_json(self, filepath: str):
        """Save all knowledge chunks to a JSON file."""
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved {len(self.chunks)} chunks → {filepath}")

    def print_summary(self):
        """Print summary of knowledge base chunks by type."""
        type_counts = {}
        for c in self.chunks:
            t = c.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1
        print("\n  Knowledge Base Summary:")
        for t, count in sorted(type_counts.items()):
            print(f"    {t:25s}: {count} chunks")
        print(f"    {'TOTAL':25s}: {len(self.chunks)} chunks")

    def load_from_transactions(self, transactions: list) -> pd.DataFrame:
        """Load from SMB user transaction list."""
        if not transactions:
            raise ValueError("No transactions provided")
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        return df

    def load_from_dict(self, data: dict) -> pd.DataFrame:
        """Load from API request dict."""
        return pd.DataFrame(data)
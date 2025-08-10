from typing import List, Dict, Tuple

from src.models.keyword import Keyword


class ShoppingCampaignGenerator:
    """Suggest CPC bids for manual Shopping based on CPC benchmarks and budgets."""

    def __init__(self, shopping_budget: float, target_conversion_rate: float = 0.02):
        self.shopping_budget = shopping_budget
        self.target_conversion_rate = target_conversion_rate

    @staticmethod
    def calculate_target_cpc(target_cpa: float, conversion_rate: float) -> float:
        return round(target_cpa * conversion_rate, 2)

    def suggest_product_bids(
        self,
        product_keywords: List[Keyword],
        target_cpa: float,
    ) -> List[Dict]:
        """Generate bid suggestions using keyword CPC ranges and ROAS intuition.

        Returns a list of dicts: {product_hint, suggested_cpc, cpc_low, cpc_high}
        """
        if not product_keywords:
            return []

        target_cpc = self.calculate_target_cpc(target_cpa, self.target_conversion_rate)

        suggestions: List[Dict] = []
        for kw in sorted(product_keywords, key=lambda k: k.relevance_score, reverse=True)[:50]:
            low = kw.metrics.top_of_page_bid_low
            high = kw.metrics.top_of_page_bid_high

            # Anchor around target CPC within observed range
            suggested = max(low, min(target_cpc, high))

            suggestions.append({
                'product_hint': kw.term,
                'suggested_cpc': round(suggested, 2),
                'cpc_low': round(low, 2),
                'cpc_high': round(high, 2)
            })

        return suggestions



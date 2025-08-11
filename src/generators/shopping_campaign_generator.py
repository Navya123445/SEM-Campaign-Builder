from typing import List, Dict, Tuple

from src.models.keyword import Keyword


class ShoppingCampaignGenerator:
    """Suggest CPC bids for manual Shopping based on CPC benchmarks and budgets."""

    def __init__(self, shopping_budget: float, target_conversion_rate: float = 0.02):
        self.shopping_budget = shopping_budget
        self.target_conversion_rate = target_conversion_rate

    @staticmethod
    def calculate_target_cpc(target_cpa: float, conversion_rate: float) -> float:
        """
        Calculate Target CPC for maximum ROAS
        
        Correct Formula: Target CPC = Target CPA × Conversion Rate
        Where Target CPA = Maximum amount you're willing to pay per acquisition
        
        Example: If you want max ₹500 per customer, and CVR = 2%
        Target CPC = ₹500 × 0.02 = ₹10 (max per click)
        """
        if conversion_rate <= 0:
            raise ValueError("Conversion rate must be positive")
        
        target_cpc = target_cpa * conversion_rate
        return round(target_cpc, 2)
    
    @staticmethod
    def calculate_target_cpa_from_budget(shopping_budget: float, target_conversions: int) -> float:
        """
        Calculate Target CPA based on budget and desired conversions
        
        Formula: Target CPA = Total Budget / Target Conversions
        """
        if target_conversions <= 0:
            raise ValueError("Target conversions must be positive")
            
        return shopping_budget / target_conversions

    def suggest_product_bids(
        self,
        product_keywords: List[Keyword],
        target_cpa: float = None,
    ) -> List[Dict]:
        """
        Generate ROAS-optimized bid suggestions using advanced prioritization.
        
        Prioritizes keywords based on:
        1. High search volume (more traffic potential)
        2. Reasonable competition (cost efficiency) 
        3. Commercial intent (conversion potential)
        4. CPC efficiency (within budget constraints)
        
        Returns a list of dicts with ROAS optimization metrics
        """
        if not product_keywords:
            return []

        # Calculate Target CPA from budget if not provided
        if target_cpa is None:
            # Assume we want 10-20 conversions from shopping budget
            estimated_conversions = max(10, int(self.shopping_budget / 60))  # $60 per conversion baseline
            target_cpa = self.calculate_target_cpa_from_budget(self.shopping_budget, estimated_conversions)
        
        target_cpc = self.calculate_target_cpc(target_cpa, self.target_conversion_rate)
        
        print(f"🎯 Shopping Bid Calculation:")
        print(f"   - Shopping Budget: ${self.shopping_budget:,.2f}")
        print(f"   - Target CPA: ${target_cpa:.2f}")
        print(f"   - Target CPC: ${target_cpc:.2f}")
        print(f"   - Conversion Rate: {self.target_conversion_rate*100:.1f}%")

        # Calculate ROAS scores for each keyword
        scored_keywords = []
        for kw in product_keywords:
            roas_score = self._calculate_roas_score(kw, target_cpc)
            scored_keywords.append((kw, roas_score))

        # Sort by ROAS score (highest potential return first)
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        
        suggestions: List[Dict] = []
        total_suggested_spend = 0
        
        for kw, roas_score in scored_keywords[:30]:  # Top 30 keywords
            low = kw.metrics.top_of_page_bid_low
            high = kw.metrics.top_of_page_bid_high
            
            # Smart CPC suggestion based on ROAS potential
            if roas_score >= 0.8:  # High ROAS potential
                suggested = min(high * 0.9, target_cpc * 1.2)  # Aggressive bidding
            elif roas_score >= 0.6:  # Medium ROAS potential  
                suggested = min(high * 0.7, target_cpc)  # Standard bidding
            else:  # Lower ROAS potential
                suggested = min(high * 0.5, target_cpc * 0.8)  # Conservative bidding
            
            # Ensure within market range
            suggested = max(low, min(suggested, high))
            
            # Budget constraint check
            estimated_monthly_spend = suggested * kw.metrics.average_monthly_searches * 0.01  # 1% CTR assumption
            if total_suggested_spend + estimated_monthly_spend <= self.shopping_budget:
                suggestions.append({
                    'product_hint': kw.term,
                    'suggested_cpc': round(suggested, 2),
                    'cpc_low': round(low, 2),
                    'cpc_high': round(high, 2),
                    'search_volume': kw.metrics.average_monthly_searches,
                    'roas_score': round(roas_score, 2),
                    'estimated_monthly_spend': round(estimated_monthly_spend, 2),
                    'priority': self._get_priority_label(roas_score)
                })
                total_suggested_spend += estimated_monthly_spend
            
            # Stop if budget exhausted
            if total_suggested_spend >= self.shopping_budget * 0.9:  # Use 90% of budget
                break

        print(f"📊 Generated {len(suggestions)} ROAS-optimized bid suggestions")
        print(f"💰 Total estimated monthly spend: ${total_suggested_spend:,.2f}")
        
        return suggestions
    
    def _calculate_roas_score(self, keyword: Keyword, target_cpc: float) -> float:
        """
        Calculate ROAS potential score (0.0 to 1.0)
        
        Factors:
        - Search Volume (higher = better reach)
        - CPC Efficiency (lower cost = better ROAS)
        - Commercial Intent (buying keywords = better conversion)
        - Competition Level (medium competition = sweet spot)
        """
        term = keyword.term.lower()
        volume = keyword.metrics.average_monthly_searches
        cpc_avg = (keyword.metrics.top_of_page_bid_low + keyword.metrics.top_of_page_bid_high) / 2
        competition = keyword.metrics.competition_level.value.lower()
        
        # Volume Score (0.0-0.3)
        if volume >= 50000:
            volume_score = 0.3
        elif volume >= 10000:
            volume_score = 0.25
        elif volume >= 1000:
            volume_score = 0.2
        else:
            volume_score = 0.1
        
        # CPC Efficiency Score (0.0-0.3)
        if cpc_avg <= target_cpc * 0.5:
            efficiency_score = 0.3  # Very affordable
        elif cpc_avg <= target_cpc:
            efficiency_score = 0.25  # Affordable
        elif cpc_avg <= target_cpc * 1.5:
            efficiency_score = 0.15  # Expensive but manageable
        else:
            efficiency_score = 0.05  # Too expensive
        
        # Commercial Intent Score (0.0-0.3)
        commercial_terms = ['buy', 'purchase', 'software', 'solution', 'platform', 'tool', 'service', 'management']
        intent_score = 0.1  # Base score
        for term_word in commercial_terms:
            if term_word in term:
                intent_score += 0.025
        intent_score = min(intent_score, 0.3)
        
        # Competition Score (0.0-0.1)
        if competition == 'medium':
            comp_score = 0.1  # Sweet spot
        elif competition == 'low':
            comp_score = 0.08  # Good but maybe low demand
        else:  # high
            comp_score = 0.05  # Expensive
        
        total_score = volume_score + efficiency_score + intent_score + comp_score
        return min(total_score, 1.0)
    
    def _get_priority_label(self, roas_score: float) -> str:
        """Get priority label based on ROAS score"""
        if roas_score >= 0.8:
            return "HIGH"
        elif roas_score >= 0.6:
            return "MEDIUM" 
        else:
            return "LOW"



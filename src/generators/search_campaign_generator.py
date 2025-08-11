from typing import List
from src.models.keyword import Keyword, AdGroup, SearchCampaign

class SearchCampaignGenerator:
    def __init__(self, budget: float, target_conversion_rate: float = 0.02):
        self.budget = budget
        self.target_conversion_rate = target_conversion_rate
    
    def create_search_campaign(self, ad_groups: List[AdGroup]) -> SearchCampaign:
        """Create complete search campaign (PDF Deliverable 1)"""
        print(f"🎯 Creating search campaign with {len(ad_groups)} ad groups...")
        
        # Optimize ad groups for budget
        optimized_ad_groups = self._optimize_ad_groups_for_budget(ad_groups)
        
        # Create campaign
        campaign = SearchCampaign(
            name="SEM Campaign - Search",
            ad_groups=optimized_ad_groups,
            total_budget=self.budget,
            target_conversion_rate=self.target_conversion_rate
        )
        
        # Calculate campaign metrics
        total_keywords = sum(len(ag.keywords) for ag in optimized_ad_groups)
        avg_cpc = self._calculate_average_cpc(optimized_ad_groups)
        
        print(f"✅ Campaign created:")
        print(f"   - Ad Groups: {len(optimized_ad_groups)}")
        print(f"   - Total Keywords: {total_keywords}")
        print(f"   - Budget: ${self.budget:,.2f}")
        print(f"   - Estimated Avg CPC: ${avg_cpc:.2f}")
        
        return campaign
    
    def _optimize_ad_groups_for_budget(self, ad_groups: List[AdGroup]) -> List[AdGroup]:
        """Optimize ad groups based on available budget"""
        
        if not ad_groups:
            return ad_groups
        
        # Calculate total estimated spend
        total_estimated_spend = 0
        for ag in ad_groups:
            avg_group_cpc = (ag.suggested_cpc_range[0] + ag.suggested_cpc_range[1]) / 2
            keyword_count = len(ag.keywords)
            estimated_group_spend = avg_group_cpc * keyword_count * 30  # Monthly estimate
            total_estimated_spend += estimated_group_spend
        
        # If total spend is within budget, return as is
        if total_estimated_spend <= self.budget:
            return ad_groups
        
        # Otherwise, prioritize ad groups by performance potential
        prioritized_groups = self._prioritize_ad_groups(ad_groups)
        
        # Select ad groups that fit within budget
        optimized_groups = []
        running_spend = 0
        
        for ag in prioritized_groups:
            avg_group_cpc = (ag.suggested_cpc_range[0] + ag.suggested_cpc_range[1]) / 2
            keyword_count = len(ag.keywords)
            estimated_group_spend = avg_group_cpc * keyword_count * 30
            
            if running_spend + estimated_group_spend <= self.budget:
                optimized_groups.append(ag)
                running_spend += estimated_group_spend
            else:
                # Try to fit some keywords from this group
                remaining_budget = self.budget - running_spend
                max_keywords = int(remaining_budget / (avg_group_cpc * 30))
                
                if max_keywords > 0:
                    # Create smaller ad group with top keywords
                    top_keywords = sorted(ag.keywords, key=lambda k: k.relevance_score, reverse=True)[:max_keywords]
                    
                    smaller_ag = AdGroup(
                        name=f"{ag.name} (Optimized)",
                        intent_category=ag.intent_category,
                        keywords=top_keywords,
                        suggested_cpc_range=ag.suggested_cpc_range,
                        theme_description=ag.theme_description
                    )
                    optimized_groups.append(smaller_ag)
                break
        
        return optimized_groups
    
    def _prioritize_ad_groups(self, ad_groups: List[AdGroup]) -> List[AdGroup]:
        """Prioritize ad groups for maximum ROAS using advanced scoring"""
        
        # Calculate ROAS scores for each ad group
        scored_ad_groups = []
        for ag in ad_groups:
            roas_score = self._calculate_ad_group_roas_score(ag)
            scored_ad_groups.append((ag, roas_score))
        
        # Sort by ROAS score (highest first)
        scored_ad_groups.sort(key=lambda x: x[1], reverse=True)
        
        # Print prioritization results
        print(f"📊 Ad Group ROAS Prioritization:")
        for ag, score in scored_ad_groups:
            print(f"   - {ag.name}: {score:.2f} ROAS score ({len(ag.keywords)} keywords)")
        
        return [ag for ag, score in scored_ad_groups]
    
    def _calculate_ad_group_roas_score(self, ad_group: AdGroup) -> float:
        """
        Calculate ROAS potential score for an ad group (0.0 to 1.0)
        
        Factors:
        - Intent Category (brand = highest, commercial = high, informational = lower)
        - Keyword Volume (total search potential)
        - CPC Efficiency (lower costs = better ROAS)
        - Keyword Count (diversification)
        """
        if not ad_group.keywords:
            return 0.0
        
        # Intent Category Score (0.0-0.4)
        intent = ad_group.intent_category.lower()
        if 'brand' in intent:
            intent_score = 0.4  # Highest converting
        elif 'commercial' in intent or 'competitor' in intent:
            intent_score = 0.35  # High converting
        elif 'category' in intent or 'product' in intent:
            intent_score = 0.3  # Good converting
        elif 'location' in intent:
            intent_score = 0.25  # Moderate converting
        else:  # long-tail, informational
            intent_score = 0.15  # Lower converting
        
        # Volume Score (0.0-0.3)
        total_volume = sum(kw.metrics.average_monthly_searches for kw in ad_group.keywords)
        if total_volume >= 100000:
            volume_score = 0.3
        elif total_volume >= 50000:
            volume_score = 0.25
        elif total_volume >= 10000:
            volume_score = 0.2
        else:
            volume_score = 0.1
        
        # CPC Efficiency Score (0.0-0.2)
        avg_cpc = (ad_group.suggested_cpc_range[0] + ad_group.suggested_cpc_range[1]) / 2
        if avg_cpc <= 1.0:
            efficiency_score = 0.2  # Very efficient
        elif avg_cpc <= 2.0:
            efficiency_score = 0.15  # Efficient
        elif avg_cpc <= 4.0:
            efficiency_score = 0.1  # Moderate
        else:
            efficiency_score = 0.05  # Expensive
        
        # Diversification Score (0.0-0.1)
        keyword_count = len(ad_group.keywords)
        if keyword_count >= 20:
            diversification_score = 0.1
        elif keyword_count >= 10:
            diversification_score = 0.08
        elif keyword_count >= 5:
            diversification_score = 0.05
        else:
            diversification_score = 0.02
        
        total_score = intent_score + volume_score + efficiency_score + diversification_score
        return min(total_score, 1.0)
    
    def _calculate_average_cpc(self, ad_groups: List[AdGroup]) -> float:
        """Calculate weighted average CPC across all ad groups"""
        
        if not ad_groups:
            return 0.0
        
        total_weighted_cpc = 0
        total_keywords = 0
        
        for ag in ad_groups:
            avg_group_cpc = (ag.suggested_cpc_range[0] + ag.suggested_cpc_range[1]) / 2
            keyword_count = len(ag.keywords)
            
            total_weighted_cpc += avg_group_cpc * keyword_count
            total_keywords += keyword_count
        
        return total_weighted_cpc / total_keywords if total_keywords > 0 else 0.0

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
        print(f"   - Budget: ₹{self.budget:,.2f}")
        print(f"   - Estimated Avg CPC: ₹{avg_cpc:.2f}")
        
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
        """Prioritize ad groups by performance potential"""
        
        def group_score(ad_group: AdGroup) -> float:
            if not ad_group.keywords:
                return 0.0
            
            # Calculate average relevance score
            avg_relevance = sum(kw.relevance_score for kw in ad_group.keywords) / len(ad_group.keywords)
            
            # Calculate efficiency (lower CPC is better)
            avg_cpc = (ad_group.suggested_cpc_range[0] + ad_group.suggested_cpc_range[1]) / 2
            efficiency = max(0, (5.0 - avg_cpc) / 5.0)  # Normalize assuming max CPC of 5
            
            # Combine metrics
            return (avg_relevance * 0.7) + (efficiency * 0.3)
        
        return sorted(ad_groups, key=group_score, reverse=True)
    
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

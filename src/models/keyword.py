from dataclasses import dataclass, asdict
from typing import Optional, List
from enum import Enum

class MatchType(Enum):
    EXACT = "exact"
    PHRASE = "phrase" 
    BROAD = "broad"  # Replaces Broad Match Modifier

class CompetitionLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class KeywordMetrics:
    """Step 4: 3 Performance Indicators from PDF"""
    average_monthly_searches: int  # Primary metric 1
    top_of_page_bid_low: float    # Primary metric 2 (Low)
    top_of_page_bid_high: float   # Primary metric 2 (High) 
    competition_level: CompetitionLevel  # Primary metric 3

@dataclass
class Keyword:
    term: str
    metrics: KeywordMetrics
    suggested_match_type: MatchType = MatchType.BROAD
    relevance_score: float = 0.0
    ad_group_assignment: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for YAML export"""
        return {
            'term': self.term,
            'search_volume': self.metrics.average_monthly_searches,
            'bid_low': self.metrics.top_of_page_bid_low,
            'bid_high': self.metrics.top_of_page_bid_high,
            'competition': self.metrics.competition_level.value,
            'match_type': self.suggested_match_type.value,
            'relevance_score': round(self.relevance_score, 2)
        }

@dataclass
class AdGroup:
    """Deliverable 1: Ad Group Structure"""
    name: str
    intent_category: str  # Brand Terms, Category Terms, etc.
    keywords: List[Keyword]
    suggested_cpc_range: tuple
    theme_description: str
    
    def to_dict(self):
        """Convert to dictionary for YAML export"""
        return {
            'name': self.name,
            'intent_category': self.intent_category,
            'theme_description': self.theme_description,
            'suggested_cpc_low': self.suggested_cpc_range[0],
            'suggested_cpc_high': self.suggested_cpc_range[1],
            'keyword_count': len(self.keywords),
            'keywords': [kw.to_dict() for kw in self.keywords]
        }

@dataclass
class SearchCampaign:
    """Deliverable 1: Complete Search Campaign"""
    name: str
    ad_groups: List[AdGroup]
    total_budget: float
    target_conversion_rate: float = 0.02
    
    def to_dict(self):
        """Convert to dictionary for YAML export"""
        total_keywords = sum(len(ag.keywords) for ag in self.ad_groups)
        return {
            'campaign_name': self.name,
            'total_budget': self.total_budget,
            'target_conversion_rate': self.target_conversion_rate,
            'total_ad_groups': len(self.ad_groups),
            'total_keywords': total_keywords,
            'ad_groups': [ag.to_dict() for ag in self.ad_groups]
        }

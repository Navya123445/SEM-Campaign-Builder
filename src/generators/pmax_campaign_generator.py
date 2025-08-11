from typing import List, Dict
from collections import defaultdict

from src.models.keyword import Keyword


class PMaxCampaignGenerator:
    """Generate Performance Max asset group themes from high-performing keywords."""

    def __init__(self, top_n: int = 50):
        self.top_n = top_n

    def create_asset_group_themes(self, keywords: List[Keyword]) -> Dict[str, List[str]]:
        """Return dict of theme_name -> top keywords supporting the theme."""
        if not keywords:
            return {}

        # Use top N by relevance
        top_keywords = sorted(keywords, key=lambda k: k.relevance_score, reverse=True)[: self.top_n]

        themes: Dict[str, List[str]] = defaultdict(list)

        # Product Category Themes
        category_terms = [
            'platform', 'software', 'tools', 'ai', 'marketing', 
            'analytics', 'dashboard', 'reporting', 'automation'
        ]

        # Use-case Based Themes
        usecase_terms = ['automation', 'insights', 'campaigns', 'social media', 'advertising', 'lead generation', 'customer service']
        # Demographic Themes
        demographic_terms = ['enterprise', 'b2b', 'startup', 'small business', 'corporate']
        # Seasonal/Event Themes (generic placeholders)
        seasonal_terms = ['2025', 'q4', 'festival', 'holiday', 'back to school']

        for kw in top_keywords:
            t = kw.term.lower()
            if any(ct in t for ct in category_terms):
                themes['Product Category Themes'].append(kw.term)
            if any(uc in t for uc in usecase_terms):
                themes['Use-case Based Themes'].append(kw.term)
            if any(dm in t for dm in demographic_terms):
                themes['Demographic Themes'].append(kw.term)
            if any(se in t for se in seasonal_terms):
                themes['Seasonal/Event-Based Themes'].append(kw.term)

        # Deduplicate and cap
        for k, v in list(themes.items()):
            dedup = []
            seen = set()
            for term in v:
                low = term.lower()
                if low not in seen:
                    seen.add(low)
                    dedup.append(term)
            themes[k] = dedup[:15]

        return dict(themes)

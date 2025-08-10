from transformers import pipeline
from typing import List, Dict
import json
import re
from src.models.keyword import Keyword, AdGroup, MatchType, CompetitionLevel


class HuggingFaceProcessor:
    def __init__(self, settings: Dict):
        self.settings = settings
        print("🤗 Initializing Hugging Face zero-shot classifier for grouping...")
        
        self.zero_shot = None
        try:
            # DistilBERT MNLI is reasonably small and good for zero-shot classification
            self.zero_shot = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
            print("✅ Zero-shot classifier loaded")
        except Exception as e:
            print(f"⚠️  Zero-shot classifier unavailable: {e}")
            print("🔄 Using enhanced rule-based grouping")
    
    def process_raw_keywords(self, raw_keywords: List[Dict], min_volume: int = 500) -> List[Keyword]:
        """Convert raw keyword data to Keyword objects with filtering"""
        print(f"🔄 Processing {len(raw_keywords)} raw keywords...")
        
        processed_keywords = []
        
        for kw_data in raw_keywords:
            keyword_text = kw_data.get('keyword', '').strip()
            search_volume = int(kw_data.get('search_volume', 0))
            
            if search_volume < min_volume:
                continue
            
            # Parse competition level
            competition_str = kw_data.get('competition', 'medium').lower()
            if competition_str == 'low':
                competition = CompetitionLevel.LOW
            elif competition_str == 'high':
                competition = CompetitionLevel.HIGH
            else:
                competition = CompetitionLevel.MEDIUM
            
            # Create keyword metrics
            from src.models.keyword import KeywordMetrics
            metrics = KeywordMetrics(
                average_monthly_searches=search_volume,
                top_of_page_bid_low=float(kw_data.get('cpc_low', 0.5)),
                top_of_page_bid_high=float(kw_data.get('cpc_high', 2.0)),
                competition_level=competition
            )
            
            keyword = Keyword(
                term=keyword_text,
                metrics=metrics,
                suggested_match_type=self._suggest_match_type(keyword_text, metrics)
            )
            
            processed_keywords.append(keyword)
        
        # Calculate relevance scores
        scored_keywords = self._calculate_relevance_scores(processed_keywords)
        scored_keywords.sort(key=lambda k: k.relevance_score, reverse=True)
        
        # Optimize keyword count: keep only high-quality keywords (target 150-200)
        relevance_threshold = 0.4  # Only keep keywords with relevance >= 0.4
        high_quality_keywords = [kw for kw in scored_keywords if kw.relevance_score >= relevance_threshold]
        
        # Cap at 200 keywords for quality
        if len(high_quality_keywords) > 200:
            high_quality_keywords = high_quality_keywords[:200]
        
        print(f"✅ Processed {len(high_quality_keywords)} high-quality keywords (filtered from {len(scored_keywords)} total)")
        return high_quality_keywords
    
    def _suggest_match_type(self, keyword_text: str, metrics) -> MatchType:
        """Suggest match type based on keyword characteristics"""
        word_count = len(keyword_text.split())
        search_volume = metrics.average_monthly_searches
        
        if any(brand in keyword_text.lower() for brand in ['cubehq', 'cube hq']):
            return MatchType.EXACT
        elif word_count <= 2 and search_volume > 2000:
            return MatchType.PHRASE
        elif word_count >= 4:
            return MatchType.EXACT
        else:
            return MatchType.BROAD
    
    def _calculate_relevance_scores(self, keywords: List[Keyword]) -> List[Keyword]:
        """Calculate relevance scores with focus on BI/analytics relevance and quality"""
        if not keywords:
            return keywords
        
        max_volume = max(kw.metrics.average_monthly_searches for kw in keywords)
        max_cpc = max(kw.metrics.top_of_page_bid_high for kw in keywords)
        
        for keyword in keywords:
            term_lower = keyword.term.lower()
            
            # Base volume score (30% weight)
            volume_score = (keyword.metrics.average_monthly_searches / max_volume) * 0.3
            
            # Competition scoring (20% weight)
            comp_scores = {
                CompetitionLevel.LOW: 0.2,
                CompetitionLevel.MEDIUM: 0.15,
                CompetitionLevel.HIGH: 0.1
            }
            competition_score = comp_scores[keyword.metrics.competition_level]
            
            # CPC efficiency (20% weight)
            avg_cpc = (keyword.metrics.top_of_page_bid_low + keyword.metrics.top_of_page_bid_high) / 2
            cpc_efficiency = max(0, (max_cpc - avg_cpc) / max_cpc) * 0.2
            
            # Business relevance bonus (30% weight) - Most important!
            relevance_bonus = 0.0
            
            # High-value BI terms
            if any(high_value in term_lower for high_value in ['business intelligence', 'bi software', 'analytics platform']):
                relevance_bonus += 0.25
            elif any(bi_term in term_lower for bi_term in ['analytics', 'dashboard', 'reporting', 'data visualization']):
                relevance_bonus += 0.2
            elif any(general_bi in term_lower for general_bi in ['data', 'insights', 'intelligence']):
                relevance_bonus += 0.1
            
            # Brand terms get high relevance
            if any(brand in term_lower for brand in ['cubehq', 'cube']):
                relevance_bonus += 0.2
            
            # Commercial intent
            if any(commercial in term_lower for commercial in ['software', 'platform', 'tool', 'solution']):
                relevance_bonus += 0.15
            
            # Penalize irrelevant/fragmented terms
            if any(irrelevant in term_lower for irrelevant in ['get', 'see', 'more', 'over', 'the', 'and']):
                relevance_bonus -= 0.1
            
            keyword.relevance_score = min(1.0, volume_score + competition_score + cpc_efficiency + relevance_bonus)
        
        return keywords
    
    def create_ad_groups_with_llm(self, keywords: List[Keyword], max_groups: int = 15) -> List[AdGroup]:
        """Create ad groups using Hugging Face model or enhanced rules"""
        print(f"🤗 Creating ad groups from {len(keywords)} keywords using LLM classification when available...")
        
        if self.zero_shot is not None:
            try:
                return self._create_zero_shot_groups(keywords, max_groups)
            except Exception as e:
                print(f"❌ Zero-shot grouping failed: {e}")
        
        return self._create_enhanced_rule_based_groups(keywords, max_groups)
    
    def _create_zero_shot_groups(self, keywords: List[Keyword], max_groups: int) -> List[AdGroup]:
        """Group keywords by zero-shot classification into intent buckets."""
        labels = [
            'Brand & Company Terms',
            'Core Business Intelligence',
            'Commercial Intent High-Value',
            'Data Analytics Solutions',
            'Enterprise & B2B Focus',
            'Long-Tail Opportunities',
            'Competitive Analysis',
            'Technical Features'
        ]
        group_meta = {
            'Brand & Company Terms': ('Brand Terms', 'Keywords containing brand names and company-specific terms'),
            'Core Business Intelligence': ('Category Terms', 'Primary business intelligence and analytics keywords'),
            'Commercial Intent High-Value': ('Commercial Intent', 'Keywords showing strong buying intent and commercial value'),
            'Data Analytics Solutions': ('Product-specific Terms', 'Specific data analytics and dashboard-related keywords'),
            'Enterprise & B2B Focus': ('Category Terms', 'Enterprise-focused and B2B-targeted keywords'),
            'Long-Tail Opportunities': ('Long-Tail Informational Queries', 'Specific, lower competition long-tail keywords'),
            'Competitive Analysis': ('Competitor Terms', 'Keywords related to competitor analysis and comparison'),
            'Technical Features': ('Product-specific Terms', 'Technical features and capabilities keywords')
        }

        buckets: Dict[str, List[Keyword]] = {k: [] for k in labels}

        for kw in keywords:
            text = kw.term
            # Quick override for brand/competitor heuristics
            low = text.lower()
            if any(b in low for b in ['cubehq', 'cube hq']):
                buckets['Brand & Company Terms'].append(kw)
                continue
            if any(c in low for c in ['reputation', 'birdeye', 'podium', 'compare', 'vs', 'alternative']):
                buckets['Competitive Analysis'].append(kw)
                continue

            res = self.zero_shot(text, candidate_labels=labels, multi_label=True)
            # Pick top label
            top_label = res['labels'][0] if res and res.get('labels') else 'Core Business Intelligence'
            buckets[top_label].append(kw)

        ad_groups: List[AdGroup] = []
        for name, kws in buckets.items():
            if not kws:
                continue
            cpc_range = self._calculate_group_cpc_range(kws)
            intent, desc = group_meta[name]
            ad_groups.append(AdGroup(name=name, intent_category=intent, keywords=kws, suggested_cpc_range=cpc_range, theme_description=desc))

        return ad_groups[:max_groups]
    
    def _create_enhanced_rule_based_groups(self, keywords: List[Keyword], max_groups: int) -> List[AdGroup]:
        """Enhanced rule-based grouping with AI-inspired logic"""
        
        groups = {
            'Brand Terms': {
                'keywords': [],
                'intent': 'Brand Terms',
                'description': 'Brand name variations and company-specific terms (CubeHQ, brand + modifiers)'
            },
            'Location-based Queries': {
                'keywords': [],
                'intent': 'Location-based Queries',
                'description': 'Geographic-targeted business intelligence and analytics keywords'
            },
            'Core Business Intelligence': {
                'keywords': [],
                'intent': 'Category Terms',
                'description': 'Primary business intelligence and analytics keywords'
            },
            'Commercial Intent High-Value': {
                'keywords': [],
                'intent': 'Commercial Intent',
                'description': 'Keywords showing strong buying intent and commercial value'
            },
            'Data Analytics Solutions': {
                'keywords': [],
                'intent': 'Product-specific Terms',
                'description': 'Specific data analytics and dashboard-related keywords'
            },
            'Long-Tail Opportunities': {
                'keywords': [],
                'intent': 'Long-Tail Informational Queries',
                'description': 'Specific, lower competition long-tail keywords'
            },
            'Competitive Analysis': {
                'keywords': [],
                'intent': 'Competitor Terms',
                'description': 'Keywords related to competitor analysis and comparison'
            },
            'Technical Features': {
                'keywords': [],
                'intent': 'Product-specific Terms',
                'description': 'Technical features and capabilities keywords'
            }
        }
        
        for keyword in keywords:
            term_lower = keyword.term.lower()
            word_count = len(keyword.term.split())
            search_volume = keyword.metrics.average_monthly_searches
            
            # Smart grouping logic - Brand Terms first (highest priority)
            if any(brand in term_lower for brand in ['cubehq', 'cube hq', 'cube', 'login', 'demo', 'pricing', 'reviews', 'alternatives']) and any(context in term_lower for context in ['cubehq', 'cube']):
                groups['Brand Terms']['keywords'].append(keyword)
                
            # Location-based queries (specific geographic terms)
            elif any(location in term_lower for location in ['bengaluru', 'mumbai', 'delhi', 'hyderabad', 'bangalore', 'chennai', 'pune', 'kolkata']) or ' in ' in term_lower:
                groups['Location-based Queries']['keywords'].append(keyword)
                
            elif any(commercial in term_lower for commercial in ['buy', 'purchase', 'pricing', 'cost', 'service', 'company', 'provider', 'vendor', 'subscription', 'plan']):
                groups['Commercial Intent High-Value']['keywords'].append(keyword)
                
            elif any(bi_term in term_lower for bi_term in ['business intelligence', 'bi tool', 'bi platform', 'intelligence platform', 'bi software']):
                groups['Core Business Intelligence']['keywords'].append(keyword)
                
            elif any(data_term in term_lower for data_term in ['data analytics', 'analytics platform', 'data visualization', 'dashboard', 'reporting', 'analytics software']):
                groups['Data Analytics Solutions']['keywords'].append(keyword)
                
            elif word_count >= 4 or (search_volume < 1000 and keyword.metrics.competition_level == CompetitionLevel.LOW):
                groups['Long-Tail Opportunities']['keywords'].append(keyword)
                
            elif any(competitor in term_lower for competitor in ['reputation', 'birdeye', 'podium', 'vs', 'compare', 'alternative', 'competitor']):
                groups['Competitive Analysis']['keywords'].append(keyword)
                
            else:
                # Default to the most appropriate group based on search volume
                if search_volume > 2000:
                    groups['Core Business Intelligence']['keywords'].append(keyword)
                else:
                    groups['Data Analytics Solutions']['keywords'].append(keyword)
        
        # Convert to AdGroup objects
        ad_groups = []
        for group_name, group_data in groups.items():
            if group_data['keywords']:  # Only create non-empty groups
                cpc_range = self._calculate_group_cpc_range(group_data['keywords'])
                
                ad_group = AdGroup(
                    name=group_name,
                    intent_category=group_data['intent'],
                    keywords=group_data['keywords'],
                    suggested_cpc_range=cpc_range,
                    theme_description=group_data['description']
                )
                ad_groups.append(ad_group)
        
        return ad_groups[:max_groups]
    
    def _calculate_group_cpc_range(self, keywords: List[Keyword]) -> tuple:
        """Calculate CPC range for ad group"""
        if not keywords:
            return (0.5, 2.0)
        
        total_volume = sum(kw.metrics.average_monthly_searches for kw in keywords)
        if total_volume == 0:
            return (0.5, 2.0)
        
        weighted_low = sum(
            kw.metrics.top_of_page_bid_low * kw.metrics.average_monthly_searches 
            for kw in keywords
        ) / total_volume
        
        weighted_high = sum(
            kw.metrics.top_of_page_bid_high * kw.metrics.average_monthly_searches 
            for kw in keywords
        ) / total_volume
        
        return (round(weighted_low, 2), round(weighted_high, 2))

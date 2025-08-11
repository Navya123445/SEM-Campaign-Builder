import requests
from bs4 import BeautifulSoup
import time
import random
import re
from typing import List, Dict
import sys
import os

# Add project root to path to import scrapper
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from scrapper import scrape_wordstream_keywords, save_to_csv

class KeywordResearcher:
    def __init__(self, settings: Dict, inputs: Dict = None):
        self.settings = settings
        self.inputs = inputs or {}  # Store inputs for dynamic brand/location access
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def research_keywords_from_seeds(self, seed_keywords: List[str]) -> List[Dict]:
        """Generate keywords from seed keywords using WordStream scraper and deterministic expansion."""
        all_keywords: List[Dict] = []
        
        print(f"🌱 Researching {len(seed_keywords)} seed keywords...")
        
        # Check if WordStream scraping is enabled
        scraping_enabled = self.settings.get('keyword_research', {}).get('wordstream_scraping', {}).get('enabled', True)
        
        # Use WordStream scraper ONCE for the brand website (not per seed)
        if scraping_enabled:
            print(f"🚀 Running WordStream analysis once for brand website...")
            try:
                # Get brand URL from inputs.yaml
                brand_url = self.inputs.get('brand_inputs', {}).get('brand_website', "https://cubehq.ai/")
                scraped_data = scrape_wordstream_keywords(brand_url)
                
                if scraped_data and len(scraped_data) > 0:
                    print(f"✅ WordStream extracted {len(scraped_data)} total keywords from brand website")
                    
                    # Convert all scraped data to our format
                    converted_keywords = []
                    for item in scraped_data:
                        converted = self._convert_scraped_to_format(item)
                        if converted:
                            converted_keywords.append(converted)
                    
                    all_keywords.extend(converted_keywords)
                    print(f"📊 Added {len(converted_keywords)} keywords from WordStream")
                    
                    # Save scraped data for reference
                    save_data = self.settings.get('keyword_research', {}).get('wordstream_scraping', {}).get('save_scraped_data', True)
                    if save_data:
                        filename = f"output/scraped_keywords_brand_website.csv"
                        os.makedirs("output", exist_ok=True)
                        save_to_csv(scraped_data, filename)
                        print(f"💾 Brand website scraped data saved to: {filename}")
                
            except Exception as e:
                print(f"⚠️ WordStream scraping failed: {e}")
                print("🔄 Continuing with deterministic expansion only")
        
        # Check settings for expansion
        real_data_only = self.settings.get('keyword_research', {}).get('data_priority', {}).get('real_data_only', False)
        minimal_estimates = self.settings.get('keyword_research', {}).get('data_priority', {}).get('minimal_estimates', True)
        
        if real_data_only:
            print(f"🎯 Real data only mode - skipping all deterministic expansion")
        elif len(all_keywords) >= 20:  # Lower threshold - if we have 20+ real keywords, skip expansion
            print(f"📝 Sufficient real data ({len(all_keywords)} keywords) - skipping deterministic expansion") 
        elif len(all_keywords) < 5:
            print(f"📝 Very limited real data ({len(all_keywords)} keywords) - adding minimal expansion...")
            for i, seed in enumerate(seed_keywords[:1]):  # Only expand 1 seed
                print(f"🔍 Emergency expansion for seed: '{seed}'")
                expanded = self._expand_keyword(seed)[:2]  # Limit to 2 per seed
                all_keywords.extend(expanded)
                print(f"   ✅ Added {len(expanded)} emergency expansions")
        else:
            print(f"📝 Moderate real data ({len(all_keywords)} keywords) - no expansion needed")
        
        # Add brand terms
        brand_keywords = self._generate_brand_keywords()
        all_keywords.extend(brand_keywords)
        print(f"📊 Added {len(brand_keywords)} brand keywords")
        
        final_keywords = self._deduplicate_keywords(all_keywords)
        print(f"✅ Total keywords generated: {len(final_keywords)} (WordStream brand analysis + deterministic seed expansion + brand terms)")
        return final_keywords
    
    def research_keywords_from_website(self, website_url: str) -> List[Dict]:
        """Research keywords using real WordStream scraper."""
        print(f"🌐 Researching keywords from website: {website_url}")
        
        # Use the working WordStream scraper
        try:
            print(f"🚀 Using WordStream scraper for: {website_url}")
            scraped_data = scrape_wordstream_keywords(website_url)
            
            if scraped_data and len(scraped_data) > 0:
                # Convert scraped data to our format
                converted_keywords = []
                for item in scraped_data:
                    keyword_data = self._convert_scraped_to_format(item)
                    if keyword_data:
                        converted_keywords.append(keyword_data)
                
                print(f"✅ WordStream scraper extracted {len(converted_keywords)} keywords")
                
                # Save scraped data for reference if enabled
                save_data = self.settings.get('keyword_research', {}).get('wordstream_scraping', {}).get('save_scraped_data', True)
                if save_data:
                    filename = f"output/scraped_keywords_{website_url.replace('https://', '').replace('/', '_').replace('.', '_')}.csv"
                    os.makedirs("output", exist_ok=True)
                    save_to_csv(scraped_data, filename)
                    print(f"💾 Scraped data saved to: {filename}")
                
                return converted_keywords
            else:
                print("⚠️ No keywords from WordStream scraper, using fallback")
                
        except Exception as e:
            print(f"❌ WordStream scraper failed: {e}")
            print("🔄 Falling back to content analysis")
        
        # Fallback to content analysis
        return self._fallback_website_analysis(website_url)
    # Removed Google Ads API and Selenium scraping integrations; using deterministic methods only.

    def generate_location_keywords(self, base_keywords: List[str], locations: List[str]) -> List[Dict]:
        """Create location-augmented keyword variants for 'Location-based Queries' ad group."""
        variants: List[Dict] = []
        for term in base_keywords:
            term_clean = term.strip()
            for loc in locations:
                for pattern in [f"{term_clean} {loc}", f"{term_clean} in {loc}", f"{loc} {term_clean}"]:
                    variants.append(self._create_keyword_data_with_estimates(pattern))
        return self._deduplicate_keywords(variants)
    
    def _scrape_wordstream_keywords(self, keyword: str) -> List[Dict]:

        """Disabled: Selenium scraping removed."""
        return []
    
    def _scrape_wordstream_url_analysis(self, website_url: str) -> List[Dict]:
        """Disabled: Selenium scraping removed."""
        return []
    
    def _setup_chrome_driver(self):
        """Disabled: Selenium scraping removed."""
        raise RuntimeError("Selenium disabled")
    
    def _parse_wordstream_results(self, driver) -> List[Dict]:
        """Disabled: Selenium scraping removed."""
        return []
    
    def _alternative_parsing(self, driver) -> List[Dict]:
        """Disabled: Selenium scraping removed."""
        return []
    
    def _extract_keyword_from_row(self, row_element) -> Dict:
        """Disabled: Selenium scraping removed."""
        return None
    
    def _parse_from_page_source(self, page_source: str) -> List[Dict]:
        """Disabled: Selenium scraping removed."""
        return []
    
    def _extract_json_keywords(self, driver) -> List[Dict]:
        """Disabled: Selenium scraping removed."""
        return []
    
    def _create_keyword_data_with_estimates(self, keyword: str) -> Dict:
        """Create keyword data with realistic estimates based on keyword characteristics"""
        
        word_count = len(keyword.split())
        keyword_lower = keyword.lower()
        
        # Estimate search volume based on keyword characteristics
        if word_count <= 2:
            if any(term in keyword_lower for term in ['ai', 'software', 'platform', 'tool']):
                search_volume = random.randint(2000, 8000)
            else:
                search_volume = random.randint(1000, 5000)
        elif word_count == 3:
            search_volume = random.randint(500, 3000)
        else:
            search_volume = random.randint(200, 1500)
        
        # Estimate competition based on commercial intent (USD)
        if any(term in keyword_lower for term in ['buy', 'purchase', 'service', 'company', 'provider']):
            competition = 'high'
            cpc_low, cpc_high = 0.90, 2.40  # USD ranges
        elif any(term in keyword_lower for term in ['software', 'platform', 'solution', 'tool']):
            competition = 'medium'  
            cpc_low, cpc_high = 0.45, 1.50  # USD ranges
        else:
            competition = 'low'
            cpc_low, cpc_high = 0.15, 0.90  # USD ranges
        
        return {
            'keyword': keyword.strip(),
            'search_volume': search_volume,
            'competition': competition,
            'cpc_low': round(cpc_low, 2),
            'cpc_high': round(cpc_high, 2),
            'data_source': 'estimated'  # Mark as estimated data
        }
    
    def _fallback_website_analysis(self, website_url: str) -> List[Dict]:
        """Fallback method for website analysis if WordStream fails"""
        
        try:
            response = self.session.get(website_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract content for keyword generation
            content_keywords = self._extract_keywords_from_content(soup.get_text())
            
            print(f"✅ Fallback analysis extracted {len(content_keywords)} keywords from website content")
            return content_keywords
            
        except Exception as e:
            print(f"❌ Fallback website analysis failed: {e}")
            return []
    
    def _expand_keyword(self, seed_keyword: str) -> List[Dict]:
        """Expand a single keyword using modifiers and variations"""
        
        modifiers = {
            'commercial': ['buy', 'purchase', 'get', 'find', 'order'],
            'local': ['near me', 'local', 'nearby'],
            'comparative': ['best', 'top', 'compare', 'vs', 'review'],
            'descriptive': ['affordable', 'cheap', 'premium', 'professional', 'quality'],
            'service': ['service', 'services', 'company', 'provider', 'solution'],
            'informational': ['how to', 'what is', 'guide', 'tips']
        }
        
        expanded_keywords = []
        
        for category, modifier_list in modifiers.items():
            for modifier in modifier_list[:2]:  # Limit to 2 per category
                # Create variations
                keyword_1 = f"{modifier} {seed_keyword}"
                keyword_2 = f"{seed_keyword} {modifier}"
                
                expanded_keywords.extend([
                    self._create_keyword_data_with_estimates(keyword_1),
                    self._create_keyword_data_with_estimates(keyword_2)
                ])
        
        return expanded_keywords[:15]  # Limit to 15 per seed
    
    def _extract_keywords_from_content(self, content: str) -> List[Dict]:
        """Extract potential keywords from website content"""
        
        # Clean and prepare content
        content = re.sub(r'[^\w\s]', ' ', content.lower())
        words = content.split()
        
        # Generate 2-4 word phrases
        keywords = []
        for i in range(len(words) - 1):
            # 2-word phrases
            if i < len(words) - 1:
                phrase_2 = f"{words[i]} {words[i+1]}"
                if self._is_valid_keyword(phrase_2):
                    keywords.append(phrase_2)
            
            # 3-word phrases
            if i < len(words) - 2:
                phrase_3 = f"{words[i]} {words[i+1]} {words[i+2]}"
                if self._is_valid_keyword(phrase_3):
                    keywords.append(phrase_3)
        
        # Convert to keyword data format and limit results
        unique_keywords = list(set(keywords))[:30]
        return [self._create_keyword_data_with_estimates(kw) for kw in unique_keywords]
    
    def _is_valid_keyword(self, phrase: str) -> bool:
        """Check if phrase is a valid keyword candidate with strict quality controls"""
        
        if len(phrase) < 5 or len(phrase) > 50:
            return False
        
        # Skip common stop words and fragments
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                      'it', 'is', 'are', 'was', 'were', 'get', 'see', 'over', 'more', 'all', 'this',
                      'that', 'from', 'up', 'out', 'down', 'can', 'will', 'your', 'our', 'we', 'you'}
        
        words = phrase.split()
        
        if len(words) < 2 or all(word in stop_words for word in words):
            return False
            
        # Filter out garbled text patterns
        if any(len(word) == 1 and not word.isalnum() for word in words):
            return False
            
        # Must contain at least one business-relevant term
        business_terms = {'business', 'software', 'platform', 'tool', 'solution', 'service', 
                         'analytics', 'data', 'intelligence', 'dashboard', 'reporting', 'management',
                         'system', 'application', 'technology', 'digital', 'automation', 'enterprise'}
        
        if not any(term in phrase.lower() for term in business_terms):
            return False
        
        # Skip fragmented phrases (like "the c", "over 1")
        if any(word.isdigit() and len(word) == 1 for word in words):
            return False
            
        return True
    
    def _generate_brand_keywords(self) -> List[Dict]:
        """Generate essential brand-specific keywords only"""
        # Extract brand name dynamically from brand website URL
        brand_website = self.inputs.get('brand_inputs', {}).get('brand_website', 'https://cubehq.ai/')
        
        # Extract brand name from URL (e.g., 'cubehq.ai' -> 'CubeHQ')
        if 'cubehq' in brand_website.lower():
            brand_name = "CubeHQ"
        elif 'yext' in brand_website.lower():
            brand_name = "Yext"
        else:
            # Generic extraction from domain name
            from urllib.parse import urlparse
            domain = urlparse(brand_website).netloc.replace('www.', '')
            brand_name = domain.split('.')[0].title()
        
        # Minimal essential brand terms only
        brand_variations = [
            brand_name.lower(),
            f"{brand_name.lower()} ai",
            f"{brand_name.lower()} platform",
            f"{brand_name.lower()} software"
        ]
        
        # Mark these as brand data, not estimated
        brand_keywords = []
        for term in brand_variations:
            brand_keywords.append({
                'keyword': term,
                'search_volume': 1200,  # Reasonable brand term volume
                'competition': 'low',
                'cpc_low': 0.30,  # $0.30 USD
                'cpc_high': 1.20,  # $1.20 USD  
                'data_source': 'brand'  # Mark as brand data
            })
        
        return brand_keywords
    
    def generate_location_keywords(self, base_keywords: List[str], locations: List[str] = None) -> List[Dict]:
        """Generate location-based keyword variants for Location-based Queries ad group"""
        # Use dynamic locations from inputs.yaml if not provided
        if locations is None:
            locations = self.inputs.get('brand_inputs', {}).get('service_locations', ['Delhi', 'Mumbai'])
        
        location_keywords = []
        
        # BI-relevant location modifiers
        location_modifiers = [
            "in {location}",
            "{location} business intelligence",
            "{location} data analytics",
            "{location} bi software",
            "{location} analytics platform",
            "business intelligence services {location}",
            "data analytics company {location}",
            "bi consultant {location}",
            "analytics solutions {location}"
        ]
        
        for location in locations:
            for modifier in location_modifiers:
                location_kw = modifier.format(location=location.lower())
                location_keywords.append(self._create_keyword_data_with_estimates(location_kw))
        
        return location_keywords
    
    def _is_relevant_to_seed(self, keyword: str, seed: str) -> bool:
        """Check if a keyword is relevant to the seed keyword"""
        keyword_lower = keyword.lower()
        seed_lower = seed.lower()
        
        # Direct match
        if seed_lower in keyword_lower:
            return True
        
        # Check if they share significant words
        seed_words = set(seed_lower.split())
        keyword_words = set(keyword_lower.split())
        
        # At least 50% overlap in words
        overlap = len(seed_words.intersection(keyword_words))
        return overlap >= max(1, len(seed_words) * 0.5)
    
    def _convert_scraped_to_format(self, scraped_item: Dict) -> Dict:
        """Convert scraped WordStream data to our internal format"""
        try:
            keyword = scraped_item.get('keyword', '').strip()
            if not keyword or keyword == 'N/A':
                return None
            
            # Parse search volume
            search_volume_str = scraped_item.get('search_volume', '0')
            if search_volume_str == 'N/A' or not search_volume_str:
                search_volume = 0
            else:
                # Remove commas and convert to int
                search_volume = int(str(search_volume_str).replace(',', '').replace('N/A', '0'))
            
            # Parse bid ranges
            bid_low_str = scraped_item.get('bid_low_range', '0.25')
            bid_high_str = scraped_item.get('bid_high_range', '1.50')
            
            try:
                # Extract numeric values from bid strings (remove currency symbols)
                bid_low = float(str(bid_low_str).replace('$', '').replace('₹', '').replace('N/A', '0.25'))
                bid_high = float(str(bid_high_str).replace('$', '').replace('₹', '').replace('N/A', '1.50'))
            except:
                bid_low, bid_high = 0.25, 1.50
            
            # Parse competition
            competition = scraped_item.get('competition', 'medium').lower()
            if competition not in ['low', 'medium', 'high']:
                competition = 'medium'
            
            return {
                'keyword': keyword,
                'search_volume': search_volume,
                'competition': competition,
                'cpc_low': round(bid_low, 2),
                'cpc_high': round(bid_high, 2),
                'data_source': 'wordstream_real'  # Mark as real data
            }
            
        except Exception as e:
            print(f"⚠️ Error converting scraped item: {e}")
            return None
    
    def _deduplicate_keywords(self, keywords: List[Dict]) -> List[Dict]:
        """Remove duplicate keywords and keep the best version"""
        
        seen_keywords = {}
        unique_keywords = []
        
        for kw_data in keywords:
            keyword = kw_data['keyword'].lower().strip()
            
            if keyword not in seen_keywords:
                seen_keywords[keyword] = True
                unique_keywords.append(kw_data)
        
        return unique_keywords

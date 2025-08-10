import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict
import re
from urllib.parse import urljoin, urlparse

class WebsiteAnalyzer:
    def __init__(self, llm_settings: Dict):
        """Initialize WebsiteAnalyzer without OpenAI dependency"""
        self.llm_settings = llm_settings
        print("ℹ️  WebsiteAnalyzer initialized - using rule-based keyword generation")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def analyze_website_content(self, url: str) -> Dict[str, any]:
        """Extract comprehensive content from website for keyword generation"""
        print(f"🔍 Analyzing website: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style content
            for script in soup(["script", "style"]):
                script.decompose()
            
            content_data = {
                'url': url,
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'headings': self._extract_headings(soup),
                'main_content': self._extract_main_content(soup),
                'navigation_items': self._extract_navigation(soup),
                'service_keywords': self._extract_service_keywords(soup),
                'product_features': self._extract_product_features(soup)
            }
            
            print(f"✅ Content extracted successfully from {url}")
            return content_data
            
        except Exception as e:
            print(f"❌ Error analyzing {url}: {str(e)}")
            return {'url': url, 'error': str(e)}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ""
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '').strip() if meta_desc else ""
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extract all headings (H1-H6)"""
        headings = []
        for i in range(1, 7):
            heading_tags = soup.find_all(f'h{i}')
            for tag in heading_tags:
                text = tag.get_text().strip()
                if text and len(text) > 3:  # Filter out very short headings
                    headings.append(text)
        return headings[:15]  # Limit to 15 most important headings
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main body content"""
        # Try common content containers
        content_selectors = [
            'main', '[role="main"]', '.content', '.main-content', 
            '.page-content', '#content', 'article'
        ]
        
        content_text = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content_text = content_elem.get_text(separator=' ', strip=True)
                break
        
        # Fallback to body if no main content found
        if not content_text:
            body = soup.find('body')
            content_text = body.get_text(separator=' ', strip=True) if body else ""
        
        # Clean and limit content
        content_text = re.sub(r'\s+', ' ', content_text)
        return content_text[:3000]  # Limit to 3000 characters
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[str]:
        """Extract navigation menu items for service discovery"""
        nav_items = []
        nav_selectors = ['nav a', '.navigation a', '.menu a', '.navbar a']
        
        for selector in nav_selectors:
            links = soup.select(selector)
            for link in links:
                text = link.get_text().strip()
                if text and len(text) > 2 and len(text) < 50:
                    nav_items.append(text)
        
        return list(set(nav_items))[:10]  # Remove duplicates, limit to 10
    
    def _extract_service_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract service-related keywords using patterns"""
        text = soup.get_text().lower()
        
        # Service-related patterns
        service_patterns = [
            r'we offer ([^.]{5,50})',
            r'our services include ([^.]{5,50})', 
            r'we provide ([^.]{5,50})',
            r'specializing in ([^.]{5,50})',
            r'solutions for ([^.]{5,50})',
            r'platform for ([^.]{5,50})'
        ]
        
        services = []
        for pattern in service_patterns:
            matches = re.findall(pattern, text)
            services.extend([match.strip() for match in matches])
        
        return services[:8]  # Return top 8 service keywords
    
    def _extract_product_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features and benefits"""
        features = []
        
        # Look for feature lists
        feature_selectors = [
            'ul li', '.features li', '.benefits li', 
            '.feature-list li', '[class*="feature"] li'
        ]
        
        for selector in feature_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text().strip()
                if 10 <= len(text) <= 80:  # Reasonable feature length
                    features.append(text)
        
        return features[:12]  # Return top 12 features
    
    def generate_seed_keywords_from_content(self, content_data: Dict) -> List[str]:
        """Generate seed keywords using intelligent rule-based approach"""
        
        print("🧠 Generating seed keywords using enhanced rule-based analysis...")
        
        # Use enhanced rule-based generation (no LLM dependency)
        return self._enhanced_seed_generation(content_data)
    
    def _enhanced_seed_generation(self, content_data: Dict) -> List[str]:
        """Enhanced rule-based seed keyword generation"""
        
        keywords = []
        
        # Extract from title (high priority)
        title = content_data.get('title', '')
        if title:
            # Full title
            keywords.append(title)
            
            # Title without company branding
            if ' - ' in title:
                main_title = title.split(' - ')[0].strip()
                keywords.append(main_title)
            
            # Extract key phrases from title
            title_words = title.split()
            if len(title_words) >= 2:
                for i in range(len(title_words) - 1):
                    phrase = ' '.join(title_words[i:i+2])
                    if len(phrase) > 5:
                        keywords.append(phrase)
        
        # Extract from meta description
        meta_desc = content_data.get('meta_description', '')
        if meta_desc:
            # Extract key phrases from meta description
            desc_phrases = self._extract_key_phrases(meta_desc)
            keywords.extend(desc_phrases[:3])
        
        # Extract from headings (medium priority)
        headings = content_data.get('headings', [])[:8]
        for heading in headings:
            if len(heading.split()) <= 4:  # Keep reasonable length
                keywords.append(heading)
        
        # Extract from navigation (business categories)
        nav_items = content_data.get('navigation_items', [])[:5]
        for nav in nav_items:
            if len(nav.split()) <= 3 and nav.lower() not in ['home', 'about', 'contact', 'blog']:
                keywords.append(nav)
        
        # Extract from service keywords
        services = content_data.get('service_keywords', [])[:5]
        for service in services:
            # Clean up service descriptions
            service_clean = re.sub(r'[^\w\s]', ' ', service)
            service_clean = re.sub(r'\s+', ' ', service_clean).strip()
            if 3 <= len(service_clean.split()) <= 4:
                keywords.append(service_clean)
        
        # Extract business-relevant terms from features
        features = content_data.get('product_features', [])[:5]
        for feature in features:
            # Look for business terms in features
            business_terms = self._extract_business_terms(feature)
            keywords.extend(business_terms)
        
        # Generate industry-specific variations
        industry_keywords = self._generate_industry_keywords(keywords[:5])
        keywords.extend(industry_keywords)
        
        # Clean and deduplicate
        cleaned_keywords = self._clean_and_filter_keywords(keywords)
        
        print(f"✅ Generated {len(cleaned_keywords)} seed keywords using enhanced rules")
        return cleaned_keywords[:15]
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key 2-3 word phrases from text"""
        # Remove special characters and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        phrases = []
        
        # Generate 2-3 word phrases
        for i in range(len(words) - 1):
            if i < len(words) - 2:
                phrase_3 = ' '.join(words[i:i+3])
                if len(phrase_3) > 8:  # Minimum length
                    phrases.append(phrase_3)
            
            phrase_2 = ' '.join(words[i:i+2])
            if len(phrase_2) > 5:
                phrases.append(phrase_2)
        
        return phrases[:5]
    
    def _extract_business_terms(self, text: str) -> List[str]:
        """Extract business-relevant terms from feature text"""
        business_indicators = [
            'platform', 'software', 'solution', 'system', 'tool', 'service',
            'analytics', 'management', 'automation', 'intelligence', 'dashboard',
            'reporting', 'integration', 'optimization', 'tracking'
        ]
        
        terms = []
        text_lower = text.lower()
        words = text_lower.split()
        
        for indicator in business_indicators:
            if indicator in text_lower:
                # Find the phrase containing this indicator
                for i, word in enumerate(words):
                    if indicator in word:
                        # Get surrounding context
                        start = max(0, i-1)
                        end = min(len(words), i+2)
                        phrase = ' '.join(words[start:end])
                        if len(phrase) > 5:
                            terms.append(phrase)
                        break
        
        return terms[:3]
    
    def _generate_industry_keywords(self, base_keywords: List[str]) -> List[str]:
        """Generate industry-specific keyword variations"""
        industry_modifiers = [
            'business', 'enterprise', 'corporate', 'professional',
            'cloud', 'online', 'digital', 'ai', 'automated'
        ]
        
        variations = []
        
        for keyword in base_keywords[:3]:  # Limit base keywords
            for modifier in industry_modifiers[:3]:  # Limit modifiers
                if modifier.lower() not in keyword.lower():
                    # Add modifier before and after
                    variations.extend([
                        f"{modifier} {keyword}",
                        f"{keyword} {modifier}"
                    ])
        
        return variations[:8]
    
    def _clean_and_filter_keywords(self, keywords: List[str]) -> List[str]:
        """Clean and filter keyword list"""
        cleaned = []
        seen = set()
        
        # Common stop words to filter out
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        for keyword in keywords:
            if not keyword:
                continue
                
            # Clean the keyword
            clean_kw = re.sub(r'[^\w\s]', ' ', keyword)
            clean_kw = re.sub(r'\s+', ' ', clean_kw).strip().lower()
            
            # Filter criteria
            words = clean_kw.split()
            
            # Skip if too short, too long, or already seen
            if (len(clean_kw) < 3 or len(clean_kw) > 60 or 
                clean_kw in seen or len(words) > 5):
                continue
            
            # Skip if all words are stop words
            if all(word in stop_words for word in words):
                continue
            
            # Skip if contains only numbers
            if clean_kw.isdigit():
                continue
            
            seen.add(clean_kw)
            cleaned.append(clean_kw)
        
        return cleaned

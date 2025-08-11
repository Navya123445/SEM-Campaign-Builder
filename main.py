#!/usr/bin/env python3
"""
SEM Campaign Builder - AI Engineer Assessment
Deliverable 1: Keyword List Grouped by Ad Groups (Search Campaign)
Author: [Navya Bansal]
Date: August 2025
"""

import os
import yaml
from dotenv import load_dotenv
from typing import Dict, List
import sys

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from collectors.website_analyzer import WebsiteAnalyzer
from collectors.keyword_researcher import KeywordResearcher
from processors.huggingface_processor import HuggingFaceProcessor  # NEW: Hugging Face processor
from generators.search_campaign_generator import SearchCampaignGenerator
from generators.pmax_campaign_generator import PMaxCampaignGenerator
from generators.shopping_campaign_generator import ShoppingCampaignGenerator

# Load environment variables
load_dotenv()

class SEMCampaignBuilder:
    def __init__(self, config_path="config/inputs.yaml", settings_path="config/settings.yaml"):
        """Initialize SEM Campaign Builder with configurations"""
        
        print("🚀 SEM Campaign Builder - Initializing...")
        
        # Load configurations
        self.config = self._load_yaml(config_path)
        self.settings = self._load_yaml(settings_path)
        
        if not self.config or not self.settings:
            raise Exception("Failed to load configuration files")
        
        # Validate inputs
        self._validate_inputs()
        
        # Initialize components with inputs for dynamic brand/location access
        self.website_analyzer = WebsiteAnalyzer(self.settings['llm_settings'])
        self.keyword_researcher = KeywordResearcher(self.settings, self.config)
        self.keyword_processor = HuggingFaceProcessor(self.settings, self.config)
        
        print("✅ Initialization complete!")
    
    def _load_yaml(self, file_path: str) -> Dict:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {file_path}")
            return None
        except yaml.YAMLError as e:
            print(f"❌ Error parsing YAML file {file_path}: {e}")
            return None
    
    def _validate_inputs(self):
        """Validate inputs according to PDF Step 1 requirements"""
        
        print("🔍 Validating inputs...")
        
        required_fields = {
            'brand_website': self.config['brand_inputs']['brand_website'],
            'search_ads_budget': self.config['ad_budgets']['search_ads_budget'],
            'keyword_discovery_option': self.config['keyword_discovery']['option']
        }
        
        for field, value in required_fields.items():
            if not value:
                raise ValueError(f"Required field missing: {field}")
            print(f"✅ {field}: {value}")
        
        # Validate seed keywords if Option 1 is selected
        if self.config['keyword_discovery']['option'] == 1:
            seed_keywords = self.config['keyword_discovery']['seed_keywords']
            if not seed_keywords or len(seed_keywords) < 5:
                print("⚠️  Warning: Less than 5 seed keywords provided for Option 1")
        
        print("✅ Input validation complete!")
    
    def run_deliverable_1(self):
        """Execute Deliverable 1: Keyword List Grouped by Ad Groups"""
        
        print("\n" + "="*60)
        print("🎯 DELIVERABLE 1: KEYWORD LIST GROUPED BY AD GROUPS")
        print("="*60)
        
        try:
            # Step 2: Keyword Discovery (PDF)
            raw_keywords = self._execute_keyword_discovery()
            
            # Step 3: Keyword Consolidation and Filtering (PDF)
            filtered_keywords = self._consolidate_and_filter_keywords(raw_keywords)
            
            # Step 4: Keyword Evaluation with 3 Performance Indicators (PDF)
            processed_keywords = self._process_keywords(filtered_keywords)
            
            # Deliverable 1: Create Ad Groups
            ad_groups = self._create_ad_groups(processed_keywords)
            
            # Generate Search Campaign
            search_campaign = self._generate_search_campaign(ad_groups)
            
            # Save outputs
            self._save_deliverable_1(search_campaign)
            
            print("\n✅ DELIVERABLE 1 COMPLETED SUCCESSFULLY!")
            print(f"📁 Results saved to: output/campaigns/")
            
            return search_campaign
            
        except Exception as e:
            print(f"\n❌ Error executing Deliverable 1: {e}")
            raise
    
    def _execute_keyword_discovery(self) -> List[Dict]:
        """Step 2: Keyword Discovery (PDF Options 1 & 2)"""
        
        print("\n📝 Step 2: Keyword Discovery")
        print("-" * 40)
        
        option = self.config['keyword_discovery']['option']
        all_keywords = []
        
        if option == 1:
            print("🔸 Using Option 1: Seed Keyword Approach")
            
            # Use provided seed keywords or generate from website
            seed_keywords = self.config['keyword_discovery']['seed_keywords']
            
            if not seed_keywords:
                print("   No seed keywords provided, generating from website...")
                content = self.website_analyzer.analyze_website_content(
                    self.config['brand_inputs']['brand_website']
                )
                seed_keywords = self.website_analyzer.generate_seed_keywords_from_content(content)
                print(f"   Generated {len(seed_keywords)} seed keywords")
            
            # Research keywords from seeds
            keywords = self.keyword_researcher.research_keywords_from_seeds(seed_keywords)
            all_keywords.extend(keywords)
            
        elif option == 2:
            print("🔸 Using Option 2: Website Content Analysis")
            
            # Analyze brand website
            brand_keywords = self.keyword_researcher.research_keywords_from_website(
                self.config['brand_inputs']['brand_website']
            )
            all_keywords.extend(brand_keywords)
        
        # Add competitor keyword research
        competitor_urls = self.config['brand_inputs'].get('competitor_websites', [])
        for competitor_url in competitor_urls:
            if competitor_url:  # Skip empty URLs
                print(f"   Analyzing competitor: {competitor_url}")
                competitor_keywords = self.keyword_researcher.research_keywords_from_website(competitor_url)
                all_keywords.extend(competitor_keywords)
        
        # Skip location-based expansion to preserve real data focus
        print("   🎯 Skipping location expansion to focus on real WordStream data")
        print("   📝 Location targeting will be handled at campaign level")
        
        print(f"✅ Keyword discovery complete: {len(all_keywords)} total keywords found")
        return all_keywords
    
    def _consolidate_and_filter_keywords(self, raw_keywords: List[Dict]) -> List[Dict]:
        """Step 3: Keyword Consolidation and Filtering (PDF) - Prioritize Real Data"""
        
        print("\n🔍 Step 3: Keyword Consolidation and Filtering")
        print("-" * 40)
        
        # Use minimal threshold to preserve real WordStream data
        config_min_volume = self.config['filtering_criteria']['min_search_volume'] 
        min_volume = 100  # Override to preserve real data
        print(f"🔸 Using minimal threshold ({min_volume}) to preserve real WordStream data")
        print(f"🔸 Config threshold was: {config_min_volume} (ignored for real data preservation)")
        
        # Separate real vs estimated data
        real_keywords = [kw for kw in raw_keywords if kw.get('data_source') == 'wordstream_real']
        estimated_keywords = [kw for kw in raw_keywords if kw.get('data_source') == 'estimated']
        other_keywords = [kw for kw in raw_keywords if 'data_source' not in kw]
        
        print(f"🎯 Real WordStream data: {len(real_keywords)} keywords")
        print(f"📝 Estimated data: {len(estimated_keywords)} keywords") 
        print(f"🔄 Other data: {len(other_keywords)} keywords")
        
        # Show volume distribution of real keywords
        if real_keywords:
            high_volume = [kw for kw in real_keywords if kw.get('search_volume', 0) >= 10000]
            medium_volume = [kw for kw in real_keywords if 1000 <= kw.get('search_volume', 0) < 10000] 
            low_volume = [kw for kw in real_keywords if 100 <= kw.get('search_volume', 0) < 1000]
            very_low = [kw for kw in real_keywords if kw.get('search_volume', 0) < 100]
            
            print(f"   📊 Real data volume distribution:")
            print(f"      - High volume (10K+): {len(high_volume)} keywords")
            print(f"      - Medium volume (1K-10K): {len(medium_volume)} keywords") 
            print(f"      - Low volume (100-1K): {len(low_volume)} keywords")
            print(f"      - Very low (<100): {len(very_low)} keywords")
        
        # Remove duplicates - prioritize real data
        seen_keywords = {}
        unique_keywords = []
        
        # Process real data first (highest priority)
        for kw in real_keywords:
            keyword_text = kw.get('keyword', '').lower().strip()
            if keyword_text and keyword_text not in seen_keywords:
                seen_keywords[keyword_text] = True
                unique_keywords.append(kw)
        
        # Process other data second
        for kw in other_keywords:
            keyword_text = kw.get('keyword', '').lower().strip()
            if keyword_text and keyword_text not in seen_keywords:
                seen_keywords[keyword_text] = True
                unique_keywords.append(kw)
        
        # Process estimated data last (lowest priority)
        for kw in estimated_keywords:
            keyword_text = kw.get('keyword', '').lower().strip()
            if keyword_text and keyword_text not in seen_keywords:
                seen_keywords[keyword_text] = True
                unique_keywords.append(kw)
        
        # Apply smart filtering - preserve real data, filter estimated data
        filtered_keywords = []
        for kw in unique_keywords:
            search_vol = kw.get('search_volume', 0)
            data_source = kw.get('data_source', '')
            
            # Keep almost all real WordStream data
            if data_source == 'wordstream_real':
                if search_vol >= 100:  # Very low threshold for real data
                    filtered_keywords.append(kw)
                else:
                    print(f"   ⚠️ Filtered low-volume real keyword: {kw.get('keyword')} ({search_vol} searches)")
            # Keep essential other data (brand terms, etc.) 
            elif 'data_source' not in kw:
                if search_vol >= 1000:  # Higher threshold for untagged data
                    filtered_keywords.append(kw)
            # Be very selective with estimated data
            elif data_source == 'estimated':
                if search_vol >= 5000:  # High threshold for estimated data
                    filtered_keywords.append(kw)
                else:
                    pass  # Filter out most estimated keywords
        
        # Count final data sources
        final_real = len([kw for kw in filtered_keywords if kw.get('data_source') == 'wordstream_real'])
        final_estimated = len([kw for kw in filtered_keywords if kw.get('data_source') == 'estimated'])
        final_other = len(filtered_keywords) - final_real - final_estimated
        
        print(f"   - Original keywords: {len(raw_keywords)}")
        print(f"   - After deduplication: {len(unique_keywords)}")
        print(f"   - After volume filtering: {len(filtered_keywords)}")
        print(f"   - Final real data: {final_real} keywords ({final_real/len(filtered_keywords)*100:.1f}%)")
        print(f"   - Final estimated data: {final_estimated} keywords ({final_estimated/len(filtered_keywords)*100:.1f}%)")
        print(f"✅ Consolidation and filtering complete - Real data prioritized")
        
        return filtered_keywords
    
    def _process_keywords(self, filtered_keywords: List[Dict]) -> List:
        """Step 4: Keyword Evaluation with 3 Performance Indicators (PDF)"""
        
        print("\n📈 Step 4: Keyword Evaluation (3 Performance Indicators)")
        print("-" * 40)
        print("🔸 Evaluating keywords using:")
        print("   1. Average Monthly Searches")
        print("   2. Top of Page Bid (Low & High)")
        print("   3. Competition Level")
        
        min_volume = self.config['filtering_criteria']['min_search_volume']
        processed_keywords = self.keyword_processor.process_raw_keywords(
            filtered_keywords, 
            min_volume
        )
        
        print(f"✅ Keyword evaluation complete: {len(processed_keywords)} keywords processed")
        return processed_keywords
    
    def _create_ad_groups(self, processed_keywords: List) -> List:
        """Create Ad Groups using LLM (PDF Deliverable 1)"""
        
        print("\n🎯 Creating Ad Groups (PDF Categories)")
        print("-" * 40)
        print("🔸 Target categories:")
        print("   - Brand Terms")
        print("   - Category Terms")
        print("   - Competitor Terms") 
        print("   - Location-based Queries")
        print("   - Long-Tail Informational Queries")
        
        max_groups = self.config.get('campaign_structure', {}).get('max_ad_groups', 15)
        ad_groups = self.keyword_processor.create_ad_groups_with_llm(
            processed_keywords, 
            max_groups
        )
        
        print(f"✅ Ad groups created: {len(ad_groups)} groups")
        for ag in ad_groups:
            print(f"   - {ag.name}: {len(ag.keywords)} keywords")
        
        return ad_groups
    
    def _generate_search_campaign(self, ad_groups: List) -> object:
        """Generate complete search campaign"""
        
        print("\n🚀 Generating Search Campaign")
        print("-" * 40)
        
        budget = self.config['ad_budgets']['search_ads_budget']
        conversion_rate = self.config['conversion_settings']['target_conversion_rate']
        
        generator = SearchCampaignGenerator(budget, conversion_rate)
        campaign = generator.create_search_campaign(ad_groups)
        
        return campaign

    def run_deliverable_2_pmax(self, processed_keywords: List) -> Dict:
        """Create Performance Max asset group themes from top-performing keywords."""
        print("\n🚀 Generating Performance Max Themes")
        print("-" * 40)
        pmax = PMaxCampaignGenerator(top_n=80)
        themes = pmax.create_asset_group_themes(processed_keywords)

        os.makedirs("output/reports", exist_ok=True)
        pmax_file = "output/reports/pmax_themes.yaml"
        with open(pmax_file, 'w') as f:
            yaml.dump({'pmax_themes': themes}, f, default_flow_style=False, indent=2)
        print(f"✅ PMax themes saved: {pmax_file}")
        return themes

    def run_deliverable_3_shopping(self, processed_keywords: List) -> Dict:
        """Suggest Shopping CPC bids based on CPC benchmarks, budget and 2% CVR."""
        print("\n🛒 Generating Shopping CPC Suggestions")
        print("-" * 40)
        shopping_budget = self.config['ad_budgets']['shopping_ads_budget']
        target_cvr = self.config['conversion_settings']['target_conversion_rate']
        target_cpa = max(50.0, shopping_budget * 0.02)  # simple placeholder heuristic

        generator = ShoppingCampaignGenerator(shopping_budget, target_cvr)
        # Use product-ish keywords: those with software/platform/tool/dashboard/reporting
        product_like = [
            kw for kw in processed_keywords
            if any(t in kw.term.lower() for t in ['software', 'platform', 'tool', 'dashboard', 'reporting', 'product'])
        ]
        suggestions = generator.suggest_product_bids(product_like, target_cpa)

        os.makedirs("output/reports", exist_ok=True)
        out_file = "output/reports/shopping_bid_suggestions.yaml"
        with open(out_file, 'w') as f:
            yaml.dump({'shopping_bid_suggestions': suggestions, 'target_cpc_note': 'anchored to CPC ranges and target CPA x CVR'}, f, default_flow_style=False, indent=2)
        print(f"✅ Shopping bid suggestions saved: {out_file}")
        return {'suggestions': suggestions}
    
    def _save_deliverable_1(self, campaign):
        """Save Deliverable 1 outputs"""
        
        print("\n💾 Saving Deliverable 1 Results...")
        print("-" * 40)
        
        # Ensure output directories exist
        os.makedirs("output/campaigns", exist_ok=True)
        os.makedirs("output/keywords", exist_ok=True)
        os.makedirs("output/reports", exist_ok=True)
        
        # Save main campaign file
        campaign_file = "output/campaigns/search_campaign_deliverable_1.yaml"
        with open(campaign_file, 'w') as f:
            yaml.dump(campaign.to_dict(), f, default_flow_style=False, indent=2)
        
        print(f"✅ Search campaign saved: {campaign_file}")
        
        # Save detailed keyword report
        keyword_report = self._create_keyword_report(campaign)
        keyword_file = "output/keywords/keyword_analysis_report.yaml"
        with open(keyword_file, 'w') as f:
            yaml.dump(keyword_report, f, default_flow_style=False, indent=2)
        
        print(f"✅ Keyword report saved: {keyword_file}")
        
        # Create summary report
        summary = self._create_summary_report(campaign)
        summary_file = "output/reports/deliverable_1_summary.yaml"
        with open(summary_file, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False, indent=2)
        
        print(f"✅ Summary report saved: {summary_file}")
        print(f"📁 All files saved to output/ directory")
    
    def _create_keyword_report(self, campaign) -> Dict:
        """Create detailed keyword analysis report"""
        
        report = {
            'keyword_analysis': {
                'total_keywords': sum(len(ag.keywords) for ag in campaign.ad_groups),
                'total_ad_groups': len(campaign.ad_groups),
                'budget_allocation': campaign.total_budget,
                'target_conversion_rate': campaign.target_conversion_rate
            },
            'ad_groups_breakdown': []
        }
        
        for ag in campaign.ad_groups:
            ag_data = {
                'ad_group_name': ag.name,
                'intent_category': ag.intent_category,
                'keyword_count': len(ag.keywords),
                'suggested_cpc_range': f"${ag.suggested_cpc_range[0]} - ${ag.suggested_cpc_range[1]}",
                'top_keywords': []
            }
            
            # Add top 10 keywords for this ad group
            top_keywords = sorted(ag.keywords, key=lambda k: k.relevance_score, reverse=True)[:10]
            for kw in top_keywords:
                ag_data['top_keywords'].append({
                    'keyword': kw.term,
                    'search_volume': kw.metrics.average_monthly_searches,
                    'suggested_match_type': kw.suggested_match_type.value,
                    'relevance_score': round(kw.relevance_score, 2)
                })
            
            report['ad_groups_breakdown'].append(ag_data)
        
        return report
    
    def _create_summary_report(self, campaign) -> Dict:
        """Create executive summary of Deliverable 1"""
        
        # Calculate key metrics
        total_keywords = sum(len(ag.keywords) for ag in campaign.ad_groups)
        avg_keywords_per_group = total_keywords / len(campaign.ad_groups) if campaign.ad_groups else 0
        
        # CPC analysis
        all_cpcs = []
        for ag in campaign.ad_groups:
            avg_group_cpc = (ag.suggested_cpc_range[0] + ag.suggested_cpc_range[1]) / 2
            all_cpcs.append(avg_group_cpc)
        
        avg_cpc = sum(all_cpcs) / len(all_cpcs) if all_cpcs else 0
        
        return {
            'deliverable_1_summary': {
                'campaign_name': campaign.name,
                'status': 'COMPLETED',
                'date_created': '2025-08-07',
                'key_metrics': {
                    'total_ad_groups': len(campaign.ad_groups),
                    'total_keywords': total_keywords,
                    'avg_keywords_per_group': round(avg_keywords_per_group, 1),
                    'budget_allocated': f"${campaign.total_budget:,.2f}",
                    'estimated_avg_cpc': f"${avg_cpc:.2f}",
                    'target_conversion_rate': f"{campaign.target_conversion_rate*100}%"
                },
                'ad_group_categories': [ag.intent_category for ag in campaign.ad_groups],
                'next_steps': [
                    'Review ad groups and keywords',
                    'Set up advertising account structure', 
                    'Create ad copy for each ad group',
                    'Proceed with Deliverable 2 (Performance Max themes)'
                ]
            }
        }

def main():
    """Main execution function"""
    
    try:
        # Initialize builder
        builder = SEMCampaignBuilder()
        
        # Execute Deliverable 1 and get the processed keywords
        campaign = builder.run_deliverable_1()
        
        # Get processed keywords from the campaign instead of re-running discovery
        print("\n🔄 Extracting processed keywords from Deliverable 1 for PMax and Shopping...")
        processed_keywords = []
        for ad_group in campaign.ad_groups:
            for keyword in ad_group.keywords:
                processed_keywords.append(keyword)
        
        print(f"✅ Reusing {len(processed_keywords)} processed keywords from Deliverable 1")

        # Execute Deliverable 2: PMax Themes
        builder.run_deliverable_2_pmax(processed_keywords)

        # Execute Deliverable 3: Shopping bids  
        builder.run_deliverable_3_shopping(processed_keywords)
        
        print(f"\n🎉 SUCCESS! Deliverables 1-3 completed successfully!")
        print(f"📊 Generated {len(campaign.ad_groups)} ad groups with {sum(len(ag.keywords) for ag in campaign.ad_groups)} keywords")
        print(f"💰 Budget: ${campaign.total_budget:,.2f}")
        print(f"📁 Check 'output/' folder for detailed results (campaigns, reports)")
        print(f"\n⏰ Ready for 2-day priority submission!")
        
    except Exception as e:
        print(f"\n💥 EXECUTION FAILED: {e}")
        print(f"Please check your configuration and try again.")
        raise

if __name__ == "__main__":
    main()

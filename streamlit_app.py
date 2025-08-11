import streamlit as st
import yaml
import os
import sys
import pandas as pd
from typing import Dict, List
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import tempfile

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from collectors.website_analyzer import WebsiteAnalyzer
    from collectors.keyword_researcher import KeywordResearcher
    from processors.huggingface_processor import HuggingFaceProcessor
    from generators.search_campaign_generator import SearchCampaignGenerator
    from generators.pmax_campaign_generator import PMaxCampaignGenerator
    from generators.shopping_campaign_generator import ShoppingCampaignGenerator
except ImportError as e:
    st.error(f"Import error: {e}. Make sure all required files are in the correct directory structure.")

# Page configuration
st.set_page_config(
    page_title="SEM Campaign Builder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme compatibility
st.markdown("""
<style>
    /* Main header styling - dark theme compatible */
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2980b9);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Deliverable cards - dark theme compatible */
    .deliverable-card {
        background: rgba(40, 44, 52, 0.8);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #2980b9;
        margin: 1rem 0;
        color: #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    .deliverable-card h2 {
        color: #ffffff !important;
        margin-bottom: 0.5rem;
    }
    
    /* Metric cards - dark theme compatible */
    .metric-card {
        background: rgba(50, 54, 62, 0.9);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #4a5568;
        text-align: center;
        margin: 0.5rem;
        color: #ffffff;
    }
    
    /* Success banner - dark theme compatible */
    .success-banner {
        background: rgba(16, 81, 40, 0.8);
        border: 1px solid #38a169;
        color: #9ae6b4;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .success-banner h3 {
        color: #68d391 !important;
        margin-bottom: 0.5rem;
    }
    
    /* Warning banner - dark theme compatible */
    .warning-banner {
        background: rgba(120, 63, 4, 0.8);
        border: 1px solid #d69e2e;
        color: #fbd38d;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    /* Keyword tags - dark theme compatible */
    .keyword-tag {
        background-color: rgba(66, 153, 225, 0.2) !important;
        color: #90cdf4 !important;
        border: 1px solid #4299e1;
        padding: 4px 8px;
        margin: 2px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    /* Text content - ensure visibility on dark backgrounds */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #ffffff;
    }
    
    /* Fix for white text on white background issue */
    div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    
    div[data-testid="stMarkdownContainer"] li {
        color: #ffffff !important;
    }
    
    /* Ensure bullet points are visible */
    .stMarkdown ul li::marker {
        color: #90cdf4;
    }
    
    /* Fix for expandable content */
    .streamlit-expanderHeader {
        background-color: rgba(40, 44, 52, 0.8) !important;
        color: #ffffff !important;
    }
    
    .streamlit-expanderContent {
        background-color: rgba(30, 34, 42, 0.9) !important;
        color: #ffffff !important;
        border: 1px solid #4a5568;
    }
    
    /* Plotly chart backgrounds */
    .js-plotly-plot {
        background-color: rgba(40, 44, 52, 0.8) !important;
    }
    
    /* Tab styling for dark theme */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(40, 44, 52, 0.8);
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #ffffff;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"][data-testid="stTab"]:hover {
        background-color: rgba(66, 153, 225, 0.2);
    }
    
    /* Dataframe styling for dark theme */
    .dataframe {
        background-color: rgba(40, 44, 52, 0.9) !important;
        color: #ffffff !important;
    }
    
    .dataframe th {
        background-color: rgba(50, 54, 62, 0.9) !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    .dataframe td {
        background-color: rgba(40, 44, 52, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Status message styling */
    .stStatus {
        background-color: rgba(40, 44, 52, 0.9) !important;
        color: #ffffff !important;
    }
    
    /* Info/warning message styling */
    .stAlert {
        background-color: rgba(40, 44, 52, 0.9) !important;
        color: #ffffff !important;
        border: 1px solid #4a5568;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitSEMBuilder:
    def __init__(self):
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'campaign_results' not in st.session_state:
            st.session_state.campaign_results = None
        if 'processed_keywords' not in st.session_state:
            st.session_state.processed_keywords = None
        if 'pmax_themes' not in st.session_state:
            st.session_state.pmax_themes = None
        if 'shopping_bids' not in st.session_state:
            st.session_state.shopping_bids = None
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False

    def render_header(self):
        """Render the main header"""
        st.markdown("""
        <div class="main-header">
            <h1>🚀 SEM Campaign Builder</h1>
            <p>AI-Powered Keyword Research & Campaign Generation</p>
            <p><strong>Maximum ROAS Optimization | 2% Conversion Rate Target</strong></p>
        </div>
        """, unsafe_allow_html=True)

    def render_input_form(self):
        """Render the input form for brand inputs and configuration"""
        st.header("📝 Campaign Configuration")
        
        with st.form("campaign_config"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏢 Brand Information")
                brand_website = st.text_input(
                    "Brand Website URL *", 
                    value="https://www.cubehq.ai",
                    help="Enter your main business website URL"
                )
                
                # Competitor websites (multiple)
                st.subheader("🎯 Competitor Analysis")
                competitor_1 = st.text_input("Competitor Website 1", value="https://yext.com/")
                competitor_2 = st.text_input("Competitor Website 2", value="")
                competitor_3 = st.text_input("Competitor Website 3", value="")
                
                # Service locations
                st.subheader("📍 Service Locations")
                locations_text = st.text_area(
                    "Service Locations (one per line)",
                    value="Bengaluru\nMumbai\nDelhi\nHyderabad",
                    help="Enter your target locations, one per line"
                )
                
            with col2:
                st.subheader("💰 Campaign Budgets (USD)")
                search_budget = st.number_input("Search Ads Budget", min_value=100, value=2500, step=100)
                shopping_budget = st.number_input("Shopping Ads Budget", min_value=100, value=1000, step=100)
                pmax_budget = st.number_input("Performance Max Budget", min_value=100, value=1500, step=100)
                
                st.subheader("🎯 Targeting Settings")
                conversion_rate = st.slider("Target Conversion Rate (%)", min_value=1.0, max_value=10.0, value=2.0, step=0.1) / 100
                min_search_volume = st.number_input("Minimum Search Volume", min_value=100, value=500, step=100)
                
                st.subheader("🔍 Keyword Discovery Method")
                discovery_option = st.selectbox(
                    "Choose Discovery Method",
                    options=[1, 2],
                    format_func=lambda x: "1 - Use Seed Keywords" if x == 1 else "2 - Analyze Website Content",
                    index=0
                )
            
            # Seed keywords (only show if option 1 is selected)
            if discovery_option == 1:
                st.subheader("🌱 Seed Keywords")
                seed_keywords_text = st.text_area(
                    "Seed Keywords (one per line)",
                    value="business intelligence platform\ndata analytics software\nAI powered insights\nenterprise dashboard\ndata visualization tool\nbusiness automation\npredictive analytics\ndata integration platform\nbusiness intelligence solution\nreal-time analytics",
                    height=150,
                    help="Enter your seed keywords, one per line"
                )
            
            # Submit button
            submit_button = st.form_submit_button("🚀 Generate SEM Campaign", use_container_width=True)
            
            if submit_button:
                # Validate required fields
                if not brand_website:
                    st.error("❌ Brand website URL is required!")
                    return None
                
                # Prepare competitor list
                competitors = [url.strip() for url in [competitor_1, competitor_2, competitor_3] if url.strip()]
                
                # Prepare locations list
                locations = [loc.strip() for loc in locations_text.split('\n') if loc.strip()]
                
                # Prepare seed keywords if option 1
                seed_keywords = []
                if discovery_option == 1:
                    seed_keywords = [kw.strip() for kw in seed_keywords_text.split('\n') if kw.strip()]
                
                # Create configuration dictionary
                config = {
                    'brand_inputs': {
                        'brand_website': brand_website,
                        'competitor_websites': competitors,
                        'service_locations': locations
                    },
                    'ad_budgets': {
                        'search_ads_budget': search_budget,
                        'shopping_ads_budget': shopping_budget,
                        'pmax_ads_budget': pmax_budget
                    },
                    'keyword_discovery': {
                        'option': discovery_option,
                        'seed_keywords': seed_keywords
                    },
                    'filtering_criteria': {
                        'min_search_volume': min_search_volume
                    },
                    'conversion_settings': {
                        'target_conversion_rate': conversion_rate
                    }
                }
                
                return config
        
        return None

    def create_settings_config(self):
        """Create default settings configuration"""
        return {
            'llm_settings': {
                'provider': 'huggingface',
                'model_name': 'distilbert-base-uncased-mnli'
            },
            'keyword_research': {
                'wordstream_scraping': {
                    'enabled': True,
                    'save_scraped_data': True
                },
                'data_priority': {
                    'real_data_only': False,
                    'minimal_estimates': True
                }
            }
        }

    def process_campaign(self, config):
        """Process the SEM campaign using the existing pipeline"""
        settings = self.create_settings_config()
        
        try:
            with st.status("🔄 Processing SEM Campaign...", expanded=True) as status:
                st.write("🔧 Initializing components...")
                
                # Initialize components
                website_analyzer = WebsiteAnalyzer(settings['llm_settings'])
                keyword_researcher = KeywordResearcher(settings, config)
                keyword_processor = HuggingFaceProcessor(settings, config)
                
                st.write("🌱 Discovering keywords...")
                # Execute keyword discovery
                raw_keywords = self._execute_keyword_discovery(
                    config, website_analyzer, keyword_researcher
                )
                
                st.write("🔍 Filtering and processing keywords...")
                # Filter keywords
                filtered_keywords = self._filter_keywords(raw_keywords, config)
                
                # Process keywords
                processed_keywords = keyword_processor.process_raw_keywords(
                    filtered_keywords, config['filtering_criteria']['min_search_volume']
                )
                
                st.write("🎯 Creating ad groups...")
                # Create ad groups
                ad_groups = keyword_processor.create_ad_groups_with_llm(processed_keywords, 15)
                
                st.write("🚀 Generating search campaign...")
                # Generate search campaign
                search_generator = SearchCampaignGenerator(
                    config['ad_budgets']['search_ads_budget'],
                    config['conversion_settings']['target_conversion_rate']
                )
                campaign = search_generator.create_search_campaign(ad_groups)
                
                st.write("📊 Generating Performance Max themes...")
                # Generate PMax themes
                pmax_generator = PMaxCampaignGenerator(top_n=50)
                pmax_themes = pmax_generator.create_asset_group_themes(processed_keywords)
                
                st.write("🛒 Generating shopping bid suggestions...")
                # Generate shopping bids
                shopping_generator = ShoppingCampaignGenerator(
                    config['ad_budgets']['shopping_ads_budget'],
                    config['conversion_settings']['target_conversion_rate']
                )
                
                # Filter for product-like keywords
                product_keywords = [
                    kw for kw in processed_keywords
                    if any(term in kw.term.lower() for term in ['software', 'platform', 'tool', 'dashboard', 'solution'])
                ]
                
                shopping_bids = shopping_generator.suggest_product_bids(product_keywords)
                
                status.update(label="✅ Campaign processing complete!", state="complete")
                
                # Store results in session state
                st.session_state.campaign_results = campaign
                st.session_state.processed_keywords = processed_keywords
                st.session_state.pmax_themes = pmax_themes
                st.session_state.shopping_bids = shopping_bids
                st.session_state.processing_complete = True
                
                return True
                
        except Exception as e:
            st.error(f"❌ Error processing campaign: {str(e)}")
            return False

    def _execute_keyword_discovery(self, config, website_analyzer, keyword_researcher):
        """Execute keyword discovery based on selected option"""
        option = config['keyword_discovery']['option']
        all_keywords = []
        
        if option == 1:
            # Use seed keywords
            seed_keywords = config['keyword_discovery']['seed_keywords']
            if not seed_keywords:
                # Generate from website if no seeds provided
                content = website_analyzer.analyze_website_content(config['brand_inputs']['brand_website'])
                seed_keywords = website_analyzer.generate_seed_keywords_from_content(content)
            
            keywords = keyword_researcher.research_keywords_from_seeds(seed_keywords)
            all_keywords.extend(keywords)
            
        elif option == 2:
            # Analyze website content
            brand_keywords = keyword_researcher.research_keywords_from_website(
                config['brand_inputs']['brand_website']
            )
            all_keywords.extend(brand_keywords)
            
            # Add competitor analysis
            for competitor_url in config['brand_inputs']['competitor_websites']:
                if competitor_url:
                    competitor_keywords = keyword_researcher.research_keywords_from_website(competitor_url)
                    all_keywords.extend(competitor_keywords)
        
        return all_keywords

    def _filter_keywords(self, raw_keywords, config):
        """Filter and deduplicate keywords"""
        min_volume = config['filtering_criteria']['min_search_volume']
        
        # Separate real vs estimated data
        real_keywords = [kw for kw in raw_keywords if kw.get('data_source') == 'wordstream_real']
        other_keywords = [kw for kw in raw_keywords if kw.get('data_source') != 'wordstream_real']
        
        # Remove duplicates
        seen_keywords = {}
        unique_keywords = []
        
        # Process real data first (highest priority)
        for kw in real_keywords:
            keyword_text = kw.get('keyword', '').lower().strip()
            if keyword_text and keyword_text not in seen_keywords:
                seen_keywords[keyword_text] = True
                unique_keywords.append(kw)
        
        # Process other data
        for kw in other_keywords:
            keyword_text = kw.get('keyword', '').lower().strip()
            if keyword_text and keyword_text not in seen_keywords:
                seen_keywords[keyword_text] = True
                unique_keywords.append(kw)
        
        # Apply volume filtering
        filtered_keywords = []
        for kw in unique_keywords:
            search_vol = kw.get('search_volume', 0)
            data_source = kw.get('data_source', '')
            
            # Keep real data with lower threshold
            if data_source == 'wordstream_real' and search_vol >= 100:
                filtered_keywords.append(kw)
            # Higher threshold for other data
            elif search_vol >= min_volume:
                filtered_keywords.append(kw)
        
        return filtered_keywords

    def render_deliverable_1(self):
        """Render Deliverable 1: Search Campaign Ad Groups"""
        if not st.session_state.campaign_results:
            return
            
        campaign = st.session_state.campaign_results
        
        st.markdown("""
        <div class="deliverable-card">
            <h2>🎯 Deliverable 1: Keyword List Grouped by Ad Groups (Search Campaign)</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Campaign summary
        col1, col2, col3, col4 = st.columns(4)
        
        total_keywords = sum(len(ag.keywords) for ag in campaign.ad_groups)
        avg_cpc = sum((ag.suggested_cpc_range[0] + ag.suggested_cpc_range[1]) / 2 for ag in campaign.ad_groups) / len(campaign.ad_groups)
        
        with col1:
            st.metric("Total Ad Groups", len(campaign.ad_groups))
        with col2:
            st.metric("Total Keywords", total_keywords)
        with col3:
            st.metric("Budget", f"${campaign.total_budget:,.0f}")
        with col4:
            st.metric("Avg CPC", f"${avg_cpc:.2f}")
        
        # Ad Groups breakdown
        for i, ad_group in enumerate(campaign.ad_groups):
            with st.expander(f"📁 {ad_group.name} ({len(ad_group.keywords)} keywords)", expanded=i==0):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Intent Category:** {ad_group.intent_category}")
                    st.markdown(f"**Description:** {ad_group.theme_description}")
                    st.markdown(f"**Suggested CPC Range:** ${ad_group.suggested_cpc_range[0]:.2f} - ${ad_group.suggested_cpc_range[1]:.2f}")
                
                with col2:
                    # Volume distribution chart with dark theme
                    volumes = [kw.metrics.average_monthly_searches for kw in ad_group.keywords]
                    if volumes:
                        fig = px.histogram(
                            x=volumes, 
                            nbins=10, 
                            title="Search Volume Distribution",
                            template="plotly_dark"
                        )
                        fig.update_layout(
                            height=200, 
                            showlegend=False,
                            paper_bgcolor='rgba(40,44,52,0.8)',
                            plot_bgcolor='rgba(40,44,52,0.8)',
                            font_color='white'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Keywords table
                keywords_data = []
                for kw in ad_group.keywords[:20]:  # Show top 20 keywords
                    keywords_data.append({
                        'Keyword': kw.term,
                        'Search Volume': f"{kw.metrics.average_monthly_searches:,}",
                        'Match Type': kw.suggested_match_type.value.title(),
                        'CPC Low': f"${kw.metrics.top_of_page_bid_low:.2f}",
                        'CPC High': f"${kw.metrics.top_of_page_bid_high:.2f}",
                        'Competition': kw.metrics.competition_level.value.title(),
                        'Relevance Score': f"{kw.relevance_score:.2f}"
                    })
                
                if keywords_data:
                    df = pd.DataFrame(keywords_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                if len(ad_group.keywords) > 20:
                    st.info(f"Showing top 20 keywords. Total: {len(ad_group.keywords)} keywords in this ad group.")

    def render_deliverable_2(self):
        """Render Deliverable 2: Performance Max Themes"""
        if not st.session_state.pmax_themes:
            return
            
        pmax_themes = st.session_state.pmax_themes
        
        st.markdown("""
        <div class="deliverable-card">
            <h2>📊 Deliverable 2: Search Themes for Performance Max Campaign</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if not pmax_themes:
            st.warning("⚠️ No Performance Max themes generated. This may be due to insufficient high-performing keyword categories.")
            return
        
        # Themes overview
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Themes", len(pmax_themes))
        with col2:
            total_theme_keywords = sum(len(keywords) for keywords in pmax_themes.values())
            st.metric("Total Theme Keywords", total_theme_keywords)
        with col3:
            avg_keywords_per_theme = total_theme_keywords / len(pmax_themes) if pmax_themes else 0
            st.metric("Avg Keywords/Theme", f"{avg_keywords_per_theme:.1f}")
        
        # Display each theme
        for theme_name, keywords in pmax_themes.items():
            with st.expander(f"🎨 {theme_name} ({len(keywords)} keywords)", expanded=True):
                
                if keywords:
                    # Create keyword tags with dark theme styling
                    keyword_tags = ""
                    for keyword in keywords[:15]:  # Show top 15 keywords
                        keyword_tags += f'<span class="keyword-tag">{keyword}</span> '
                    
                    st.markdown(f"**Top Keywords:** {keyword_tags}", unsafe_allow_html=True)
                    
                    if len(keywords) > 15:
                        st.info(f"Showing top 15 keywords. Total: {len(keywords)} keywords in this theme.")
                    
                    # Asset group guidance
                    st.markdown("**Asset Group Recommendations:**")
                    if "Product Category" in theme_name:
                        st.markdown("• Focus on product features and benefits in headlines")
                        st.markdown("• Use high-quality product imagery")
                        st.markdown("• Highlight unique selling propositions")
                    elif "Use-case" in theme_name:
                        st.markdown("• Create scenario-based ad copy")
                        st.markdown("• Show practical applications")
                        st.markdown("• Include customer success stories")
                    elif "Demographic" in theme_name:
                        st.markdown("• Tailor messaging to target audience")
                        st.markdown("• Use relevant imagery and language")
                        st.markdown("• Focus on specific pain points")
                    elif "Seasonal" in theme_name:
                        st.markdown("• Time-sensitive messaging")
                        st.markdown("• Seasonal imagery and offers")
                        st.markdown("• Limited-time promotions")
                else:
                    st.write("No keywords found for this theme.")

    def render_deliverable_3(self):
        """Render Deliverable 3: Shopping Campaign Bid Suggestions"""
        if not st.session_state.shopping_bids:
            return
            
        shopping_bids = st.session_state.shopping_bids
        
        st.markdown("""
        <div class="deliverable-card">
            <h2>🛒 Deliverable 3: Suggested CPC Bids for Manual Shopping Campaign</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if not shopping_bids:
            st.warning("⚠️ No shopping bid suggestions generated. This may be due to insufficient product-related keywords.")
            return
        
        # Shopping campaign summary
        total_estimated_spend = sum(bid.get('estimated_monthly_spend', 0) for bid in shopping_bids)
        high_priority_bids = [bid for bid in shopping_bids if bid.get('priority') == 'HIGH']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Products", len(shopping_bids))
        with col2:
            st.metric("High Priority", len(high_priority_bids))
        with col3:
            st.metric("Est. Monthly Spend", f"${total_estimated_spend:,.0f}")
        with col4:
            avg_suggested_cpc = sum(bid.get('suggested_cpc', 0) for bid in shopping_bids) / len(shopping_bids)
            st.metric("Avg Suggested CPC", f"${avg_suggested_cpc:.2f}")
        
        # Priority distribution chart with dark theme
        priority_counts = {}
        for bid in shopping_bids:
            priority = bid.get('priority', 'UNKNOWN')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        if priority_counts:
            fig = px.pie(
                values=list(priority_counts.values()),
                names=list(priority_counts.keys()),
                title="Bid Priority Distribution",
                template="plotly_dark"
            )
            fig.update_layout(
                paper_bgcolor='rgba(40,44,52,0.8)',
                plot_bgcolor='rgba(40,44,52,0.8)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Bid suggestions table
        bid_data = []
        for bid in shopping_bids:
            bid_data.append({
                'Product/Keyword': bid.get('product_hint', 'N/A'),
                'Suggested CPC': f"${bid.get('suggested_cpc', 0):.2f}",
                'CPC Range': f"${bid.get('cpc_low', 0):.2f} - ${bid.get('cpc_high', 0):.2f}",
                'Search Volume': f"{bid.get('search_volume', 0):,}",
                'ROAS Score': f"{bid.get('roas_score', 0):.2f}",
                'Priority': bid.get('priority', 'N/A'),
                'Est. Monthly Spend': f"${bid.get('estimated_monthly_spend', 0):.0f}"
            })
        
        if bid_data:
            df = pd.DataFrame(bid_data)
            
            # Color code by priority for dark theme
            def highlight_priority(row):
                if row['Priority'] == 'HIGH':
                    return ['background-color: rgba(16, 81, 40, 0.6); color: #9ae6b4'] * len(row)
                elif row['Priority'] == 'MEDIUM':
                    return ['background-color: rgba(120, 63, 4, 0.6); color: #fbd38d'] * len(row)
                else:
                    return ['background-color: rgba(84, 29, 49, 0.6); color: #feb2b2'] * len(row)
            
            styled_df = df.style.apply(highlight_priority, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Bidding strategy recommendations
            st.markdown("### 💡 Bidding Strategy Recommendations")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **High Priority Products:**
                • Start with suggested CPC or slightly higher
                • Monitor closely for performance
                • Increase bids for top performers
                • Target 80% impression share
                """)
            
            with col2:
                st.markdown("""
                **Medium/Low Priority Products:**
                • Start with conservative bids (suggested CPC × 0.8)
                • Test gradually with budget constraints
                • Focus on profitable keywords only
                • Target 50-60% impression share
                """)

    def render_download_section(self):
        """Render download section for campaign data"""
        if not st.session_state.processing_complete:
            return
        
        st.markdown("### 📥 Download Campaign Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Download Search Campaign", use_container_width=True):
                if st.session_state.campaign_results:
                    yaml_data = yaml.dump(st.session_state.campaign_results.to_dict(), default_flow_style=False, indent=2)
                    st.download_button(
                        label="Download YAML",
                        data=yaml_data,
                        file_name="search_campaign.yaml",
                        mime="text/yaml"
                    )
        
        with col2:
            if st.button("📊 Download PMax Themes", use_container_width=True):
                if st.session_state.pmax_themes:
                    yaml_data = yaml.dump({'pmax_themes': st.session_state.pmax_themes}, default_flow_style=False, indent=2)
                    st.download_button(
                        label="Download YAML",
                        data=yaml_data,
                        file_name="pmax_themes.yaml",
                        mime="text/yaml"
                    )
        
        with col3:
            if st.button("🛒 Download Shopping Bids", use_container_width=True):
                if st.session_state.shopping_bids:
                    yaml_data = yaml.dump({'shopping_bid_suggestions': st.session_state.shopping_bids}, default_flow_style=False, indent=2)
                    st.download_button(
                        label="Download YAML",
                        data=yaml_data,
                        file_name="shopping_bids.yaml",
                        mime="text/yaml"
                    )

    def run(self):
        """Main Streamlit app execution"""
        self.render_header()
        
        # Sidebar
        with st.sidebar:
            st.markdown("### 📋 Navigation")
            if st.session_state.processing_complete:
                st.success("✅ Campaign Generated!")
                st.markdown("**Jump to sections:**")
                if st.button("🎯 Search Campaign", use_container_width=True):
                    st.rerun()
                if st.button("📊 PMax Themes", use_container_width=True):
                    st.rerun()
                if st.button("🛒 Shopping Bids", use_container_width=True):
                    st.rerun()
            else:
                st.info("👆 Configure your campaign above to get started")
                
            st.markdown("---")
            st.markdown("### ℹ️ About")
            st.markdown("""
            This tool generates three key deliverables:
            
            1. **Search Campaign**: Keyword groups optimized for maximum ROAS
            2. **PMax Themes**: Asset group themes for Performance Max campaigns  
            3. **Shopping Bids**: CPC suggestions based on target CPA and conversion rates
            
            **Target**: 2% conversion rate optimization
            """)
        
        # Main content
        if not st.session_state.processing_complete:
            # Show input form
            config = self.render_input_form()
            
            if config:
                # Process the campaign
                success = self.process_campaign(config)
                
                if success:
                    st.balloons()
                    st.markdown("""
                    <div class="success-banner">
                        <h3>🎉 Campaign Generated Successfully!</h3>
                        <p>Your SEM campaign has been generated with maximum ROAS optimization. Scroll down to view all deliverables.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Auto-rerun to show results
                    st.rerun()
        
        # Show results if processing is complete
        if st.session_state.processing_complete:
            
            # Navigation tabs
            tab1, tab2, tab3, tab4 = st.tabs(["🎯 Search Campaign", "📊 PMax Themes", "🛒 Shopping Bids", "📥 Downloads"])
            
            with tab1:
                self.render_deliverable_1()
            
            with tab2:
                self.render_deliverable_2()
            
            with tab3:
                self.render_deliverable_3()
            
            with tab4:
                self.render_download_section()
            
            # Reset button
            st.markdown("---")
            if st.button("🔄 Start New Campaign", type="secondary"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

def main():
    """Main function to run the Streamlit app"""
    app = StreamlitSEMBuilder()
    app.run()

if __name__ == "__main__":
    main()

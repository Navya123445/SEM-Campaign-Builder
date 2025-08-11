from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import platform
import os
import shutil


def scrape_wordstream_keywords(website_url="https://cubehq.ai/"):
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Auto-download ChromeDriver with proper architecture detection
    try:
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            print("🍎 Detected Apple Silicon Mac, installing compatible ChromeDriver...")
            
            wdm_cache_path = os.path.expanduser("~/.wdm")
            if os.path.exists(wdm_cache_path):
                print("🧹 Clearing webdriver-manager cache...")
                try:
                    shutil.rmtree(wdm_cache_path)
                except Exception as cache_error:
                    print(f"⚠️ Could not clear cache: {cache_error}")
            
            chromedriver_path = ChromeDriverManager().install()
        else:
            chromedriver_path = ChromeDriverManager().install()
        
        print(f"📍 ChromeDriver path: {chromedriver_path}")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ Error setting up ChromeDriver: {e}")
        print("💡 Trying alternative ChromeDriver setup...")
        
        try:
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
            print("✅ Using ChromeDriver from system PATH")
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")
            raise e2
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    all_keywords_data = []
    
    try:
        print("📍 Navigating to WordStream...")
        driver.get("https://www.wordstream.com/keywords")
        time.sleep(5)  # 5 sec delay after navigation
        print("✅ Page loaded")
        
        # Step 1: Fill initial form
        print("🔍 Filling initial form...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "input_1_1"))
        )
        
        # Fill website URL
        url_input = driver.find_element(By.ID, "input_1_1")
        url_input.clear()
        url_input.send_keys(website_url)
        print("✅ Filled website URL")
        time.sleep(5)  # 5 sec delay after filling URL
        
        # Click submit button
        print("🔍 Clicking FIND MY KEYWORDS button...")
        submit_button = driver.find_element(By.ID, "gform_submit_button_1")
        driver.execute_script("arguments[0].click();", submit_button)
        print("✅ Clicked FIND MY KEYWORDS button")
        time.sleep(5)  # 5 sec delay after clicking submit
        
        # Step 2: Handle modal popup (if appears) - NO LOCATION CHANGES
        print("⏳ Waiting for modal popup...")
        try:
            # Wait for the modal to appear
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//h4[text()='Refine Your Search']"))
            )
            print("✅ Modal popup detected!")
            print("🌍 Using default location (no changes)")
            time.sleep(5)  # 5 sec delay after modal appears
            
            # Just click Continue button directly - no location changes
            print("➡️ Clicking Continue button with default settings...")
            try:
                continue_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "refine-continue"))
                )
                
                # Scroll button into view if needed
                driver.execute_script("arguments[0].scrollIntoView(true);", continue_button)
                time.sleep(2)
                
                # Click Continue button
                driver.execute_script("arguments[0].click();", continue_button)
                print("✅ Clicked Continue button")
                time.sleep(5)  # 5 sec delay after clicking Continue
                
            except Exception as e:
                print(f"⚠️ Could not click Continue button: {e}")
                time.sleep(5)  # 5 sec delay even on error
            
        except TimeoutException:
            print("⚠️ No modal popup found, proceeding directly...")
            time.sleep(5)  # 5 sec delay
        
        # Step 3: Extract keyword results (PAGE 1 ONLY)
        print("⏳ Waiting for keyword results...")
        try:
            # Wait for results to load
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//h4[contains(text(), 'Keyword results for')]")),
                    EC.presence_of_element_located((By.XPATH, "//table//tbody//tr"))
                )
            )
            print("✅ Keyword results loaded!")
            time.sleep(5)  # 5 sec delay after results load
            
            # Extract keyword data from PAGE 1 ONLY
            print("📄 Processing page 1 only...")
            
            try:
                # Wait for table to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table//tbody"))
                )
                
                # Extract table rows from first page
                rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
                
                if len(rows) == 0:
                    print("⚠️ No table rows found on page 1")
                else:
                    for i, row in enumerate(rows):
                        try:
                            # Extract keyword (first column - th element)
                            keyword_cell = row.find_element(By.TAG_NAME, "th")
                            keyword = keyword_cell.text.strip()
                            
                            # Skip empty keywords
                            if not keyword:
                                continue
                            
                            # Extract data cells (td elements)
                            cells = row.find_elements(By.TAG_NAME, "td")
                            
                            if len(cells) >= 4:
                                keyword_data = {
                                    'keyword': keyword,
                                    'search_volume': cells[0].text.strip().replace(',', ''),
                                    'bid_low_range': cells[1].text.strip(),
                                    'bid_high_range': cells[2].text.strip(),
                                    'competition': cells[3].text.strip()
                                }
                                all_keywords_data.append(keyword_data)
                                print(f"📝 Extracted: {keyword}")
                                
                        except Exception as e:
                            continue
                        
                        # Small delay between processing rows
                        time.sleep(0.5)
                    
                    print(f"✅ Extracted {len(rows)} keywords from page 1")
                    print(f"🛑 Stopping at page 1 as requested")
                    time.sleep(5)  # 5 sec delay after extraction
                        
            except TimeoutException:
                print("⚠️ No table found on page 1")
                time.sleep(5)  # 5 sec delay
                    
        except TimeoutException:
            print("⚠️ No keyword results found")
            time.sleep(5)  # 5 sec delay
        
        # Save page source for debugging
        try:
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("💾 Saved page source for debugging")
        except:
            pass
        
        print(f"🎉 Extraction completed! Found {len(all_keywords_data)} keywords from page 1")
        return all_keywords_data
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        
        # Save page source for debugging
        try:
            with open("error_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("💾 Saved error page source for debugging")
            print(f"📄 Current URL: {driver.current_url}")
        except:
            pass
            
        return all_keywords_data
        
    finally:
        time.sleep(2)
        driver.quit()


def save_to_csv(data, filename="keywords.csv"):
    if data and len(data) > 0:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"💾 Data saved to {filename}")
        print(f"📊 Total rows: {len(df)}")
        print("\n📈 Sample data:")
        print(df.head())
        return df
    else:
        print("⚠️ No data to save")
        return None


# Run the scraper
if __name__ == "__main__":
    print("🚀 Starting WordStream scraping (Page 1 only) with default location...")
    
    # Customize this parameter
    website_url = "https://cubehq.ai/"
    
    # Run scraper
    keywords = scrape_wordstream_keywords(website_url)
    
    # Save results
    df = save_to_csv(keywords, "wordstream_keywords_page1.csv")
    
    if df is not None:
        print(f"\n✅ Scraping completed successfully!")
        print(f"📁 Results saved to: wordstream_keywords_page1.csv")
        print(f"📊 Total keywords from page 1: {len(df)}")
    else:
        print(f"\n⚠️ No keywords extracted from page 1. Check debug_page_source.html for troubleshooting")

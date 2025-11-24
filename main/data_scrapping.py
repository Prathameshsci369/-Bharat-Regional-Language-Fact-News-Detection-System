import asyncio
import json
import re
import logging
from playwright.async_api import async_playwright
import time
from urllib.parse import urlparse, quote
import os
from datetime import datetime
import random
from bs4 import BeautifulSoup
import hashlib
import requests.utils
import traceback
from typing import List, Dict, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_search_scraper.log'),
        logging.StreamHandler()
    ]
)

class FreeProxyRotator:
    """Simple free proxy rotation with better error handling"""
    
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.failed_proxies = set()
        
    async def refresh_proxy_list(self):
        """Refresh proxy list from free sources"""
        try:
            # Using a static list of free proxies for demonstration
            # In production, you might want to fetch from free proxy APIs
            new_proxies = [
                # Format: "server:port" or "username:password@server:port"
                "us1.proxysite.com:8080",
                "uk.proxysite.com:8080",
                "de.proxysite.com:8080",
                # Add more free proxies as needed
            ]
            
            # Filter out previously failed proxies
            self.proxies = [p for p in new_proxies if p not in self.failed_proxies]
            self.current_index = 0
            logging.info(f"Refreshed proxy list with {len(self.proxies)} proxies")
        except Exception as e:
            logging.error(f"Failed to refresh proxy list: {str(e)}")
            self.proxies = []
    
    def get_next_proxy(self):
        """Get next proxy from the list"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def mark_proxy_failed(self, proxy):
        """Mark a proxy as failed"""
        self.failed_proxies.add(proxy)
        if proxy in self.proxies:
            self.proxies.remove(proxy)
        logging.warning(f"Marked proxy as failed: {proxy}")

class WebSearchScraper:
    """Main class for web search and scraping functionality"""
    
    def __init__(self, 
                 min_scraped_pages: int = 6, 
                 max_scraped_pages: int = 8,
                 exclude_domains: List[str] = None,
                 headless: bool = False,
                 output_dir: str = "./results"):
        """
        Initialize the web search scraper
        
        Args:
            min_scraped_pages: Minimum number of quality pages to scrape
            max_scraped_pages: Maximum number of pages to scrape
            exclude_domains: List of domains to exclude from results
            headless: Whether to run browser in headless mode
            output_dir: Directory to save results
        """
        self.search_results = {}
        self.visited_links = []
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Initialize proxy rotator
        self.proxy_rotator = FreeProxyRotator()
        
        # Search engines to try in order
        self.search_engines = [
            {
                "name": "Bing", 
                "url": "https://www.bing.com", 
                "search_path": "/search?q=",
                "direct_search_url": "https://www.bing.com/search?q={query}"
            },
            {
                "name": "StartPage", 
                "url": "https://www.startpage.com", 
                "search_path": "/do/search?query=",
                "direct_search_url": "https://www.startpage.com/do/search?query={query}"
            }
        ]
        
        # Track which search engines are blocked
        self.blocked_engines = set()
        
        # Configuration parameters
        self.min_scraped_pages = min_scraped_pages
        self.max_scraped_pages = max_scraped_pages
        self.headless = headless
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Default exclude domains if not provided
        if exclude_domains is None:
            self.exclude_domains = [
                'facebook.com',
                'twitter.com',
                'instagram.com',
                'linkedin.com',
                'youtube.com',
                'pinterest.com',
                'reddit.com',
                'apps.apple.com',
                'play.google.com',
                'duck.ai'
            ]
        else:
            self.exclude_domains = exclude_domains
    
    def get_random_user_agent(self):
        """Get random user agent"""
        return random.choice(self.user_agents)
    
    def human_like_delay(self, min_seconds=1, max_seconds=4):
        """Generate human-like random delay"""
        delay = random.uniform(min_seconds, max_seconds)
        return delay
    
    def get_domain_name(self, url):
        """Extract domain name from URL"""
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc.replace('www.', '')
        except:
            return "unknown"
    
    def extract_clean_links(self, html_content, engine_name="Bing"):
        """Extract URLs from search results based on the search engine"""
        soup = BeautifulSoup(html_content, 'html.parser')
        clean_links = []
        
        if engine_name == "Bing":
            # Bing's main search result structure
            result_elements = soup.select('li.b_algo, .b_algo')
            
            for result in result_elements:
                # Get the main link from the result
                link_element = result.select_one('h2 a, .b_title a, a[href]')
                if link_element:
                    href = link_element.get('href', '')
                    if href and href.startswith('http'):
                        # Clean the URL
                        clean_url = self.clean_bing_url(href)
                        if clean_url and clean_url not in clean_links:
                            clean_links.append(clean_url)
            
            # If no structured results, try alternative approach
            if not clean_links:
                logging.warning(f"No structured results found for {engine_name}, trying alternative selectors")
                result_elements = soup.select('a[href]')
                for result in result_elements:
                    href = result.get('href', '')
                    if href and href.startswith('http') and 'bing.com' not in href:
                        clean_url = self.clean_bing_url(href)
                        if clean_url and clean_url not in clean_links:
                            clean_links.append(clean_url)
        
        elif engine_name == "StartPage":
            # StartPage search result structure
            result_elements = soup.select('.w-gl__result, .result')
            
            for result in result_elements:
                link_element = result.select_one('h3 a, a[href]')
                if link_element:
                    href = link_element.get('href', '')
                    if href and href.startswith('http') and 'startpage.com' not in href:
                        clean_url = self.clean_generic_url(href)
                        if clean_url and clean_url not in clean_links:
                            clean_links.append(clean_url)
            
            # If no structured results, try alternative approach
            if not clean_links:
                logging.warning(f"No structured results found for {engine_name}, trying alternative selectors")
                result_elements = soup.select('a[href]')
                for result in result_elements:
                    href = result.get('href', '')
                    if href and href.startswith('http') and 'startpage.com' not in href:
                        clean_url = self.clean_generic_url(href)
                        if clean_url and clean_url not in clean_links:
                            clean_links.append(clean_url)
        
        # If still no structured results, try generic approach
        if not clean_links:
            logging.warning(f"No structured results found for {engine_name}, using generic extraction")
            # Look for any links that look like search results
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if ('http' in href and 
                    engine_name.lower() not in href.lower() and
                    not any(domain in href.lower() for domain in ['microsoft', 'google']) and
                    not href.endswith(('.jpg', '.png', '.gif'))):
                    clean_url = self.clean_generic_url(href)
                    if clean_url and clean_url not in clean_links:
                        clean_links.append(clean_url)
        
        return clean_links[:20]  # Return more links to increase chances of getting good ones
    
    def clean_bing_url(self, url):
        """Clean URLs from Bing search results"""
        # Remove tracking parameters and clean URL
        if 'bing.com' in url and '/ck/' in url:
            # Bing redirect URL - extract actual URL
            match = re.search(r'u=([^&]+)', url)
            if match:
                import urllib.parse
                actual_url = urllib.parse.unquote(match.group(1))
                url = actual_url
        
        # Remove common Bing tracking
        url = re.sub(r'&r=.*', '', url)
        url = re.sub(r'&c=.*', '', url)
        
        # Basic validation
        if (url.startswith(('http://', 'https://')) and
            len(url) > 10 and
            '.' in url and
            ' ' not in url):
            return url.split('&')[0]  # Remove any remaining parameters
        
        return None
    
    def clean_generic_url(self, url):
        """Clean and validate generic URLs"""
        # Remove common tracking parameters
        url = re.sub(r'[?&](utm_|ref|source|campaign|medium).*?(&|$)', '', url)
        
        # Basic validation
        if (url.startswith(('http://', 'https://')) and
            len(url) > 10 and
            '.' in url and
            ' ' not in url):
            return url.split('&')[0]  # Remove any remaining parameters
        
        return None
    
    def clean_content_with_regex(self, text):
        """Clean and extract meaningful content using regex patterns"""
        if not text:
            return ""
        
        # Remove script and style tags content
        text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', text, flags=re.IGNORECASE)
        
        # Remove HTML tags but keep content
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common unwanted patterns
        unwanted_patterns = [
            r'<!--.*?-->',  # HTML comments
            r'\{.*?\}',     # JSON-like content
            r'&\w+;',       # HTML entities
        ]
        
        for pattern in unwanted_patterns:
            text = re.sub(pattern, '', text)
        
        return text.strip()
    
    def validate_content_quality(self, content):
        """Validate if scraped content is of good quality"""
        if not content:
            return False
        
        # Remove HTML tags if any
        text = re.sub(r'<[^>]+>', ' ', content)
        
        # Count words
        words = text.split()
        
        # Check if content has enough words
        if len(words) < 100:
            return False
        
        # Check if content has meaningful sentences
        sentences = re.split(r'[.!?]+', text)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(meaningful_sentences) < 5:
            return False
        
        return True
    
    async def setup_stealth_mode(self, page):
        """Enhanced stealth mode to avoid bot detection"""
        try:
            # Random user agent
            await page.set_extra_http_headers({
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            })
            
            # Set viewport
            viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1536, 'height': 864},
                {'width': 1440, 'height': 900},
            ]
            viewport = random.choice(viewports)
            await page.set_viewport_size(viewport)
            
            # Enhanced JavaScript evasions
            await page.add_init_script("""
                // Remove webdriver traces
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }
                    ],
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Override permissions
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {
                        return {
                            requestTime: Date.now() / 1000 - 0.2,
                            startLoadTime: Date.now() / 1000 - 0.2,
                            commitLoadTime: Date.now() / 1000 - 0.1,
                            finishDocumentLoadTime: Date.now() / 1000 - 0.05,
                            finishLoadTime: Date.now() / 1000 - 0.01,
                            firstPaintAfterLoadTime: 0,
                            firstPaintTime: Date.now() / 1000 - 0.15,
                            navigationType: "Other",
                            wasFetchedViaSpdy: false,
                            wasNpnNegotiated: false
                        };
                    },
                    csi: function() {
                        return {
                            pageT: Date.now() / 1000,
                            startE: Date.now() / 1000 - 0.2,
                            tran: 15
                        };
                    }
                };
                
                // Override the permissions query method
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override WebGL Vendor
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
                
                // Override battery API
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            """)
            
        except Exception as e:
            logging.debug(f"Stealth mode setup: {str(e)}")
    
    async def human_like_mouse_movements(self, page):
        """Simulate human-like mouse movements and scrolling"""
        try:
            # Get viewport size
            viewport = page.viewport_size
            if viewport:
                # Move mouse to random positions
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Scroll randomly - improved scrolling logic
                scroll_count = random.randint(3, 8)
                for _ in range(scroll_count):
                    # Random scroll amount
                    scroll_amount = random.randint(200, 800)
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Scroll back to top
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
        except Exception as e:
            logging.debug(f"Mouse movement simulation skipped: {str(e)}")
    
    async def scroll_to_load_content(self, page, max_scrolls=5):
        """Scroll to load dynamic content on a page"""
        try:
            # Get initial page height
            last_height = await page.evaluate("document.body.scrollHeight")
            
            # Scroll down to load more content
            for i in range(max_scrolls):
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Wait for new content to load
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Calculate new scroll height and compare with last scroll height
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    # No more content loaded
                    break
                
                last_height = new_height
                
                # Random mouse movement while scrolling
                if random.random() > 0.5:  # 50% chance
                    viewport = page.viewport_size
                    if viewport:
                        x = random.randint(100, viewport['width'] - 100)
                        y = random.randint(100, viewport['height'] - 100)
                        await page.mouse.move(x, y)
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            logging.info(f"Scrolled {i+1} times to load content")
            return True
            
        except Exception as e:
            logging.error(f"Error during scrolling: {str(e)}")
            return False
    
    async def handle_captcha(self, page):
        """More accurate CAPTCHA detection and handling"""
        try:
            content = await page.content()
            page_text = content.lower()
            current_url = page.url.lower()
            
            # Strong CAPTCHA indicators
            strong_indicators = [
                (r'recaptcha', 'iframe'),
                (r'hcaptcha', 'iframe'),
                (r'challenge-platform', 'div'),
                (r'cf-challenge', 'div')
            ]
            
            # Check for strong indicators
            for pattern, tag in strong_indicators:
                if re.search(pattern, page_text):
                    # Verify it's actually in the page structure
                    elements = await page.query_selector_all(tag)
                    for element in elements:
                        html = await element.inner_html()
                        if re.search(pattern, html, re.IGNORECASE):
                            logging.warning(f"CAPTCHA confirmed: {pattern}")
                            # Try to solve CAPTCHA automatically (implementation depends on CAPTCHA type)
                            # For now, we'll just wait for manual intervention
                            logging.warning("Please solve the CAPTCHA manually. Waiting for 60 seconds...")
                            await asyncio.sleep(60)
                            
                            # Check if CAPTCHA is still present
                            new_content = await page.content()
                            if re.search(pattern, new_content.lower()):
                                return False  # CAPTCHA still present
                            else:
                                return True  # CAPTCHA solved
            
            # Check URL patterns for CAPTCHA
            captcha_url_patterns = [
                r'challenge',
                r'verify',
                r'captcha'
            ]
            
            for pattern in captcha_url_patterns:
                if re.search(pattern, current_url):
                    logging.warning(f"CAPTCHA URL detected: {current_url}")
                    logging.warning("Please solve the CAPTCHA manually. Waiting for 60 seconds...")
                    await asyncio.sleep(60)
                    
                    # Check if URL has changed (CAPTCHA solved)
                    new_url = page.url.lower()
                    if not re.search(pattern, new_url):
                        return True  # CAPTCHA solved
                    else:
                        return False  # CAPTCHA still present
            
            return True  # No CAPTCHA detected
            
        except Exception as e:
            logging.debug(f"CAPTCHA check completed: {str(e)}")
            return True
    
    def filter_search_links(self, links, engine_name):
        """Filter and clean search result links"""
        filtered_links = []
        
        # Patterns to exclude based on search engine
        exclude_patterns = {
            "Bing": [
                r'bing\.com',
                r'microsoft\.com', 
                r'live\.com',
                r'office\.com',
                r'go\.microsoft\.com',
                r'privacy',
                r'preferences',
                r'account'
            ],
            "StartPage": [
                r'startpage\.com',
                r'ixquick\.com'
            ]
        }
        
        # Common patterns to exclude
        common_patterns = [
            r'\.(png|jpg|jpeg|gif|pdf|css|js|woff|ttf)($|\?)',
        ]
        
        # Get engine-specific patterns
        engine_patterns = exclude_patterns.get(engine_name, [])
        
        for link in links:
            # Skip if matches exclude patterns
            if any(re.search(pattern, link, re.IGNORECASE) for pattern in engine_patterns + common_patterns):
                continue
                
            # Skip if domain is in exclude list
            domain = self.get_domain_name(link)
            if any(exclude_domain in domain for exclude_domain in self.exclude_domains):
                continue
                
            # Skip very short links
            if len(link) < 10:
                continue
                
            # Skip duplicate links
            if link not in filtered_links:
                filtered_links.append(link)
        
        return filtered_links
    
    async def search_engine(self, page, engine, query, use_proxy=False):
        """Search using a specific search engine with improved error handling"""
        engine_name = engine["name"]
        engine_url = engine["url"]
        search_path = engine["search_path"]
        direct_search_url = engine.get("direct_search_url", "")
        
        logging.info(f"Searching {engine_name} for: {query} (Proxy: {use_proxy})")
        
        try:
            # Setup stealth
            await self.setup_stealth_mode(page)
            await asyncio.sleep(self.human_like_delay(2, 4))
            
            # Try direct URL search first (bypasses homepage)
            if direct_search_url:
                try:
                    encoded_query = quote(query)
                    search_url = direct_search_url.format(query=encoded_query)
                    logging.info(f"Trying direct search URL for {engine_name}")
                    await page.goto(search_url, timeout=30000, wait_until='networkidle')
                    
                    # Check if we're blocked
                    page_content = await page.content()
                    if 'blocked' in page_content.lower() or 'captcha' in page_content.lower():
                        logging.warning(f"Direct search URL blocked for {engine_name}")
                        raise Exception(f"{engine_name} blocked access")
                    
                    # Wait for results
                    await page.wait_for_load_state('networkidle')
                    
                    # Add human-like behavior on search results page
                    await self.human_like_mouse_movements(page)
                    
                    # Scroll to load more results if needed
                    await self.scroll_to_load_content(page, max_scrolls=3)
                    
                    # Check for blocks
                    final_content = await page.content()
                    if 'no results' in final_content.lower() or 'blocked' in final_content.lower():
                        logging.warning(f"Possible block detected on {engine_name} - no results found")
                        return []
                    
                    # Extract links
                    links = self.extract_clean_links(final_content, engine_name)
                    filtered_links = self.filter_search_links(links, engine_name)
                    
                    return filtered_links
                    
                except Exception as e:
                    logging.warning(f"Direct search URL failed for {engine_name}: {str(e)}")
            
            # Fallback to navigating to the search engine homepage
            await page.goto(engine_url, timeout=30000, wait_until='networkidle')
            
            # Check if we're blocked immediately
            page_content = await page.content()
            if 'blocked' in page_content.lower() or 'captcha' in page_content.lower():
                logging.error(f"{engine_name} blocked access immediately")
                return []
            
            # Find search box using multiple approaches
            search_box = await self.find_search_box(page, engine_name)
            
            if search_box:
                # Use JavaScript to set value (more reliable)
                await page.evaluate(f'(element) => element.value = "{query}"', search_box)
                await asyncio.sleep(1)
                await search_box.press('Enter')
            else:
                # Direct URL fallback
                encoded_query = quote(query)
                search_url = f"{engine_url}{search_path}{encoded_query}"
                await page.goto(search_url, timeout=30000, wait_until='networkidle')
            
            # Wait for results
            await page.wait_for_load_state('networkidle')
            
            # Add human-like behavior on search results page
            await self.human_like_mouse_movements(page)
            
            # Scroll to load more results if needed
            await self.scroll_to_load_content(page, max_scrolls=3)
            
            # Check for blocks
            final_content = await page.content()
            if 'no results' in final_content.lower() or 'blocked' in final_content.lower():
                logging.warning(f"Possible block detected on {engine_name} - no results found")
                return []
            
            # Extract links
            links = self.extract_clean_links(final_content, engine_name)
            filtered_links = self.filter_search_links(links, engine_name)
            
            return filtered_links
            
        except Exception as e:
            logging.error(f"Search on {engine_name} failed: {str(e)}")
            return []
    
    async def find_search_box(self, page, engine_name):
        """Find search box based on search engine"""
        search_selectors = {
            "Bing": ['input[name="q"]', '#sb_form_q', 'input[type="search"]'],
            "StartPage": ['input[name="query"]', '#query', 'input[type="search"]']
        }
        
        selectors = search_selectors.get(engine_name, ['input[name="q"]', 'input[type="search"]'])
        
        for selector in selectors:
            try:
                search_box = await page.wait_for_selector(selector, timeout=5000)
                if search_box:
                    return search_box
            except:
                continue
        
        return None
    
    async def search_with_fallback(self, page, query):
        """Try searching with multiple search engines as fallbacks with better error handling"""
        all_links = []
        engine_usage = {}
        connection_methods = {}
        
        # Try each search engine until we have enough links
        for engine in self.search_engines:
            engine_name = engine["name"]
            
            # Skip if this engine is blocked
            if engine_name in self.blocked_engines:
                logging.info(f"Skipping {engine_name} - previously blocked")
                continue
                
            try:
                # Create a new page for this search
                search_page = await page.context.new_page()
                await self.setup_stealth_mode(search_page)
                
                # Try searching with this engine using direct connection first
                links = await self.search_engine(search_page, engine, query, use_proxy=False)
                
                if links:
                    logging.info(f"Successfully found {len(links)} links using {engine_name} (direct)")
                    all_links.extend(links)
                    engine_usage[engine_name] = engine_usage.get(engine_name, 0) + 1
                    connection_methods[f"{engine_name}:direct"] = connection_methods.get(f"{engine_name}:direct", 0) + 1
                    
                    # Remove duplicates
                    all_links = list(dict.fromkeys(all_links))
                    
                    # Check if we have enough links
                    if len(all_links) >= 15:  # Get more links to increase chances of good content
                        await search_page.close()
                        return all_links, engine_usage, connection_methods
                else:
                    logging.warning(f"No results from {engine_name} (direct)")
                    await search_page.close()
                    
                    # Check if we're blocked
                    if await self.is_engine_blocked(engine):
                        self.blocked_engines.add(engine_name)
                        logging.warning(f"{engine_name} appears to be blocked, adding to blocked list")
                    
                    # Try with proxy if available
                    proxy = self.proxy_rotator.get_next_proxy()
                    if proxy:
                        try:
                            # Create a new context with proxy
                            proxy_context = await page.context.browser.new_context(
                                proxy={"server": f"http://{proxy}"},
                                viewport={'width': 1920, 'height': 1080},
                                user_agent=self.get_random_user_agent()
                            )
                            
                            proxy_page = await proxy_context.new_page()
                            await self.setup_stealth_mode(proxy_page)
                            
                            links = await self.search_engine(proxy_page, engine, query, use_proxy=True)
                            
                            if links:
                                logging.info(f"Successfully found {len(links)} links using {engine_name} (proxy: {proxy})")
                                all_links.extend(links)
                                engine_usage[engine_name] = engine_usage.get(engine_name, 0) + 1
                                connection_methods[f"{engine_name}:proxy"] = connection_methods.get(f"{engine_name}:proxy", 0) + 1
                                
                                # Remove duplicates
                                all_links = list(dict.fromkeys(all_links))
                                
                                # Check if we have enough links
                                if len(all_links) >= 15:  # Get more links to increase chances of good content
                                    await proxy_page.close()
                                    await proxy_context.close()
                                    return all_links, engine_usage, connection_methods
                            else:
                                logging.warning(f"No results from {engine_name} (proxy: {proxy})")
                                await proxy_page.close()
                                await proxy_context.close()
                                
                                # Mark proxy as failed
                                self.proxy_rotator.mark_proxy_failed(proxy)
                                
                        except Exception as e:
                            logging.error(f"Proxy search failed for {engine_name}: {str(e)}")
                            try:
                                await proxy_page.close()
                                await proxy_context.close()
                            except:
                                pass
                            
                            # Mark proxy as failed
                            self.proxy_rotator.mark_proxy_failed(proxy)
                        
            except Exception as e:
                logging.error(f"Error searching with {engine_name}: {str(e)}")
                try:
                    await search_page.close()
                except:
                    pass
        
        # If we've tried all engines and still don't have enough links, return what we have
        if all_links:
            logging.warning(f"Only found {len(all_links)} links after trying all engines")
            return all_links, engine_usage, connection_methods
        else:
            logging.error("All search engines failed or are blocked")
            return [], engine_usage, connection_methods
    
    async def is_engine_blocked(self, engine):
        """Check if a search engine is likely blocking us"""
        # This is a simplified check - in a real implementation, you might
        # want to navigate to the engine and check for CAPTCHA or block messages
        return False
    
    async def scrape_page_content(self, page, url):
        """Scrape content with better targeting and scrolling"""
        try:
            logging.info(f"Scraping content from: {url}")
            
            # Setup stealth mode
            await self.setup_stealth_mode(page)
            
            # Navigate to page
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Wait for content to load
            await asyncio.sleep(self.human_like_delay(2, 4))
            
            # Add human-like behavior
            await self.human_like_mouse_movements(page)
            
            # Scroll to load dynamic content
            await self.scroll_to_load_content(page, max_scrolls=5)
            
            # Get page title
            title = await page.title()
            
            # Try to extract main content using multiple strategies
            content_text = await self.extract_main_content(page)
            
            # If no meaningful content found, it might be a home page
            if len(content_text.split()) < 100:
                logging.info(f"Low content on {url}, might be home page")
                content_text = await self.extract_home_page_content(page)
            
            # Validate content quality
            is_quality_content = self.validate_content_quality(content_text)
            
            return {
                'url': url,
                'title': title,
                'content': content_text[:10000],
                'content_length': len(content_text),
                'word_count': len(content_text.split()),
                'is_quality_content': is_quality_content,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'title': 'Error loading page',
                'content': f'Error: {str(e)}',
                'content_length': 0,
                'word_count': 0,
                'is_quality_content': False,
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def extract_main_content(self, page):
        """Extract main content from page"""
        content_selectors = [
            'article',
            'main',
            '.content',
            '#content',
            '.post-content',
            '.entry-content',
            '.article-content',
            'div[role="main"]'
        ]
        
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip().split()) > 50:  # Meaningful content
                        return self.clean_content_with_regex(text)
            except:
                continue
        
        # Fallback: get body content
        body = await page.query_selector('body')
        if body:
            text = await body.text_content()
            return self.clean_content_with_regex(text)
        
        return ""
    
    async def extract_home_page_content(self, page):
        """Simple home page content extraction"""
        try:
            body = await page.query_selector('body')
            if body:
                text = await body.text_content()
                return self.clean_content_with_regex(text)
            return "Home page content"
        except:
            return "Content extraction failed"
    
    def should_skip_url(self, url):
        """Check if a URL should be skipped"""
        domain = self.get_domain_name(url)
        return any(exclude_domain in domain for exclude_domain in self.exclude_domains)
    
    async def run_scraping(self, search_queries: List[str]):
        """
        Run the scraping process for the given search queries
        
        Args:
            search_queries: List of search queries to process
            
        Returns:
            Dict containing all the scraped results
        """
        # Refresh proxy list
        await self.proxy_rotator.refresh_proxy_list()
        
        async with async_playwright() as p:
            # Enhanced browser launch with better stealth
            browser = await p.chromium.launch(
                headless=self.headless,  # Use the configured headless setting
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-ipc-flooding-protection',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps',
                    '--disable-translate',
                    '--disable-extensions',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ],
                slow_mo=500  # Slow down operations
            )
            
            # Create initial context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.get_random_user_agent(),
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                storage_state=None  # Don't persist cookies between runs
            )
            
            # Rotate IP/context between queries to avoid detection
            all_results = {}
            
            for query_index, query in enumerate(search_queries):
                logging.info(f"Processing query {query_index + 1}/{len(search_queries)}: {query}")
                
                # Create a new context for each query to avoid detection
                if query_index > 0:  # Create new context for subsequent queries
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent=self.get_random_user_agent(),
                        java_script_enabled=True,
                        bypass_csp=True,
                        ignore_https_errors=True,
                        storage_state=None
                    )
                
                # Create a page for searching
                search_page = await context.new_page()
                await self.setup_stealth_mode(search_page)
                
                # Perform search with fallback engines
                links, engine_usage, connection_methods = await self.search_with_fallback(search_page, query)
                
                await search_page.close()  # Close page after search
                
                if not links:
                    logging.warning(f"No links found for query: {query}. Possible block detected.")
                    # Skip to next query
                    continue
                
                # Print links to terminal
                print(f"\n{'='*60}")
                print(f"Links found for: '{query}'")
                print(f"{'='*60}")
                for i, link in enumerate(links, 1):
                    domain = self.get_domain_name(link)
                    print(f"{i:2d}. {domain:30} {link}")
                
                # Scrape content from each link until we have enough quality content
                query_results = []
                quality_content_count = 0
                total_scraped = 0
                
                for link_index, link in enumerate(links):
                    if link in self.visited_links or self.should_skip_url(link):
                        continue
                    
                    # Stop if we have enough quality content
                    if quality_content_count >= self.min_scraped_pages:
                        logging.info(f"Successfully scraped {quality_content_count} quality pages, stopping for this query")
                        break
                    
                    # Stop if we've scraped too many pages
                    if total_scraped >= self.max_scraped_pages * 2:  # Allow double attempts to find quality content
                        logging.info(f"Scraped {total_scraped} pages, stopping for this query")
                        break
                    
                    total_scraped += 1
                    logging.info(f"Scraping {total_scraped}/{len(links)}: {self.get_domain_name(link)}")
                    
                    # Create a new page for each link to avoid detection
                    scrape_page = await context.new_page()
                    await self.setup_stealth_mode(scrape_page)
                    
                    # Handle CAPTCHA if needed
                    if not await self.handle_captcha(scrape_page):
                        logging.warning(f"CAPTCHA not solved for {link}, skipping")
                        await scrape_page.close()
                        continue
                    
                    page_data = await self.scrape_page_content(scrape_page, link)
                    
                    # Check if we got quality content
                    if page_data.get('is_quality_content', False):
                        quality_content_count += 1
                        logging.info(f"Found quality content ({quality_content_count}/{self.min_scraped_pages})")
                    
                    query_results.append(page_data)
                    self.visited_links.append(link)
                    
                    await scrape_page.close()
                    
                    # Longer delay between scrapes
                    delay = self.human_like_delay(3, 8)
                    await asyncio.sleep(delay)
                
                # Store results
                all_results[query] = {
                    'search_query': query,
                    'timestamp': datetime.now().isoformat(),
                    'engine_usage': engine_usage,
                    'connection_methods': connection_methods,
                    'links_found': links,
                    'links_count': len(links),
                    'scraped_pages': query_results,
                    'scraped_count': len(query_results),
                    'quality_content_count': quality_content_count,
                    'total_scraped': total_scraped
                }
                
                # Close context to clear all cookies and storage
                await context.close()
                
                # Longer delay between queries
                if query_index < len(search_queries) - 1:
                    delay = self.human_like_delay(10, 20)  # Much longer delay
                    logging.info(f"Long cooling period: {delay:.1f} seconds before next query...")
                    await asyncio.sleep(delay)
            
            await browser.close()
            return all_results
    
    def save_to_json(self, data: Dict, filename: str = None) -> str:
        """
        Save scraped data to JSON file
        
        Args:
            data: The data to save
            filename: Optional filename. If not provided, a timestamped filename will be generated
            
        Returns:
            The path to the saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_results_{timestamp}.json"
        
        # Ensure the filename has the correct path
        if not os.path.isabs(filename):
            filename = os.path.join(self.output_dir, filename)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Results saved to: {filename}")
            return filename
        except Exception as e:
            logging.error(f"Error saving to JSON: {str(e)}")
            return None

# Simple interface function for external use
async def search_and_scrape(
    queries: List[str], 
    min_scraped_pages: int = 6, 
    max_scraped_pages: int = 8,
    exclude_domains: List[str] = None,
    headless: bool = False,
    output_dir: str = "./results",
    output_file: str = None
) -> Dict:
    """
    Search and scrape content for the given queries
    
    Args:
        queries: List of search queries to process
        min_scraped_pages: Minimum number of quality pages to scrape
        max_scraped_pages: Maximum number of pages to scrape
        exclude_domains: List of domains to exclude from results
        headless: Whether to run browser in headless mode
        output_dir: Directory to save results
        output_file: Optional output filename
        
    Returns:
        Dict containing all the scraped results
    """
    scraper = WebSearchScraper(
        min_scraped_pages=min_scraped_pages,
        max_scraped_pages=max_scraped_pages,
        exclude_domains=exclude_domains,
        headless=headless,
        output_dir=output_dir
    )
    
    # Run the scraping process
    results = await scraper.run_scraping(queries)
    
    # Save results to JSON
    saved_file = scraper.save_to_json(results, output_file)
    
    # Add metadata to results
    results['_metadata'] = {
        'total_queries': len(queries),
        'total_links_found': sum(data['links_count'] for data in results.values() if isinstance(data, dict)),
        'total_pages_scraped': sum(data['scraped_count'] for data in results.values() if isinstance(data, dict)),
        'total_quality_pages': sum(data['quality_content_count'] for data in results.values() if isinstance(data, dict)),
        'saved_to': saved_file,
        'scraped_at': datetime.now().isoformat()
    }
    
    return results

# Example usage
if __name__ == "__main__":
    # Example queries
    example_queries = [
        "Delhi Bomb Blast",
        "Tejas Crash on Dubai"
    ]
    
    # Run the search and scrape
    results = asyncio.run(search_and_scrape(
        queries=example_queries,
        min_scraped_pages=6,
        max_scraped_pages=8,
        headless=False,
        output_dir="./results"
    ))
    
    # Print summary
    print(f"\n{'='*80}")
    print("SEARCH AND SCRAPE SUMMARY")
    print(f"{'='*80}")
    metadata = results.get('_metadata', {})
    print(f"Total queries: {metadata.get('total_queries', 0)}")
    print(f"Total links found: {metadata.get('total_links_found', 0)}")
    print(f"Total pages scraped: {metadata.get('total_pages_scraped', 0)}")
    print(f"Total quality pages: {metadata.get('total_quality_pages', 0)}")
    print(f"Results saved to: {metadata.get('saved_to', 'Unknown')}")
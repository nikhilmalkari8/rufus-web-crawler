import logging
from typing import List, Dict, Any
from playwright.async_api import BrowserContext, Page
from urllib.parse import urlparse
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rufus')

class WebScraper:
    """Enhanced web scraper with better content relevance scoring"""
    
    def __init__(self, keywords: List[str]):
        self.keywords = keywords
        self.base_domain = ""  # Will be set during crawl
        self.base_url = ""     # Complete base URL

    async def crawl_with_score_criteria(self, context: BrowserContext, start_url: str, 
                                    max_depth: int = 2, min_score: int = 100,
                                    cumulative_score_threshold: int = 300) -> List[Dict]:
        """
        Crawl the website with score-based collection and early stopping.
        - Collects pages with score >= min_score
        - Stops when the cumulative score of collected pages reaches cumulative_score_threshold
        """
        # Extract base domain and URL for relative link handling
        parsed_url = urlparse(start_url)
        
        if parsed_url.netloc:
            self.base_domain = parsed_url.netloc
            self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        else:
            # Handle case where URL might be malformed
            if '://' in start_url:
                self.base_domain = start_url.split('://', 1)[1].split('/', 1)[0]
                self.base_url = start_url.split('/', 3)[0] + '//' + self.base_domain
            else:
                self.base_domain = start_url.split('/', 1)[0]
                self.base_url = 'https://' + self.base_domain
            
        visited = set()
        queue = [(start_url, 0)]
        collected_pages = []
        stop_crawling = False
        cumulative_score = 0
        
        logger.info(f"Starting crawl from {start_url} with keywords: {self.keywords}")
        logger.info(f"Collection threshold: {min_score}, Cumulative score threshold: {cumulative_score_threshold}")
        
        while queue and not stop_crawling:
            current_url, depth = queue.pop(0)
            logger.info(f"Checking URL: {current_url} (depth {depth}/{max_depth})")
            
            if current_url in visited:
                continue
                
            if depth > max_depth:
                continue
                
            # Normalize and validate URL
            normalized_url = self._normalize_url(current_url)
            if not normalized_url:
                logger.warning(f"Skipping invalid URL: {current_url}")
                continue
                
            visited.add(normalized_url)
            
            try:
                page = await context.new_page()
                # Set a longer timeout and handle navigation errors
                await page.goto(normalized_url, timeout=45000, wait_until="domcontentloaded")
                
                # Check if page is accessible and has content
                if await self._is_valid_page(page):
                    # Extract content
                    content = await self._extract_content(page)
                    
                    # Check if content is relevant
                    relevance_score = self._check_relevance(content)
                    page_title = await self._get_page_title(page)
                    
                    logger.info(f"Page: {normalized_url} | Title: {page_title} | Score: {relevance_score}")
                    
                    if relevance_score >= min_score:
                        logger.info(f"Relevant content found at {normalized_url} (score: {relevance_score})")
                        
                        page_data = {
                            "url": normalized_url, 
                            "title": page_title,
                            "content": content,
                            "relevance_score": relevance_score
                        }
                        
                        collected_pages.append(page_data)
                        cumulative_score += relevance_score
                        
                        logger.info(f"Current cumulative score: {cumulative_score}/{cumulative_score_threshold}")
                        
                        # Check if we should stop crawling based on cumulative score
                        if cumulative_score >= cumulative_score_threshold:
                            logger.info(f"Reached cumulative score threshold of {cumulative_score_threshold}. Stopping crawl.")
                            stop_crawling = True
                    
                    # Continue crawling if not at max depth and not stopping
                    if depth < max_depth and not stop_crawling:
                        links = await self._extract_links(page)
                        # Add links to queue with priority for same domain
                        same_domain_links = []
                        external_links = []
                        
                        for link in links:
                            if link not in visited:
                                if self.base_domain in link:
                                    same_domain_links.append((link, depth + 1))
                                else:
                                    external_links.append((link, depth + 1))
                        
                        # Add same domain links first, then external links
                        queue.extend(same_domain_links)
                        queue.extend(external_links)
            
            except Exception as e:
                logger.error(f"Failed at {normalized_url}: {str(e)}")
            finally:
                await page.close()
                
        logger.info(f"Crawl completed. Collected {len(collected_pages)} relevant pages with cumulative score of {cumulative_score}.")
        
        # Sort results by relevance score
        collected_pages.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return collected_pages
    
    async def _is_valid_page(self, page: Page) -> bool:
        """Check if the page is valid and has content"""
        try:
            # Check if page has a body
            body = await page.query_selector('body')
            if not body:
                return False
                
            # Check for common error indicators
            status = await page.evaluate("() => document.querySelector('body').innerText")
            error_phrases = ["404", "not found", "access denied", "forbidden", 
                            "error", "unavailable", "sorry"]
            
            if status and len(status) < 100:  # Short page content often indicates an error
                status_lower = status.lower()
                if any(phrase in status_lower for phrase in error_phrases):
                    return False
            
            return True
        except Exception:
            return False
    
    async def _get_page_title(self, page: Page) -> str:
        """Extract the page title"""
        try:
            return await page.title()
        except Exception:
            return "Unknown Title"
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to absolute format"""
        if not url:
            return ""
            
        # Handle JavaScript links, anchors, etc.
        if url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return ""
            
        # Handle relative URLs
        if not url.startswith(('http://', 'https://')):
            if url.startswith('//'):
                # Protocol-relative URL
                return f"https:{url}"
            elif url.startswith('/'):
                # Absolute path
                return f"{self.base_url}{url}"
            else:
                # Relative path
                return f"{self.base_url}/{url}"
                
        return url
            
    async def _extract_content(self, page: Page) -> str:
        """Extract meaningful content from page with improved targeting"""
        try:
            # Try to identify and ignore navigation, footers, etc.
            await page.evaluate("""
                () => {
                    // Remove common non-content elements
                    const elementsToRemove = document.querySelectorAll('nav, footer, header, .menu, #menu, .navigation, .sidebar, #sidebar, .ads, .advertisement');
                    elementsToRemove.forEach(el => {
                        if (el) el.style.display = 'none';
                    });
                }
            """)
            
            # First try to get main content from common content containers
            content_selectors = [
                'main', 'article', '#content', '.content', '#main-content', '.main-content',
                '.post', '.entry', '.article', '.page-content', '.entry-content', 
                '[role="main"]', '.main', '#main'
            ]
            
            for selector in content_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text) > 100:  # Ignore very short content
                            texts.append(text)
                    if texts:
                        return "\n\n".join(texts)
            
            # Extract text from all paragraphs if no content containers found
            paragraphs = await page.query_selector_all('p')
            if paragraphs:
                texts = []
                for p in paragraphs:
                    text = await p.inner_text()
                    if text and len(text) > 20:  # Ignore very short paragraphs
                        texts.append(text)
                if texts:
                    return "\n\n".join(texts)
            
            # Fallback to body if no structured content found
            return await page.inner_text('body')
            
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return ""
            
    async def _extract_links(self, page: Page) -> List[str]:
        """Extract all valid links from the page"""
        try:
            all_links = []
            link_elements = await page.query_selector_all('a[href]')
            
            for link_el in link_elements:
                href = await link_el.get_attribute('href')
                if not href:
                    continue
                    
                normalized_url = self._normalize_url(href)
                if normalized_url and normalized_url not in all_links:
                    all_links.append(normalized_url)
                    
            return all_links
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []
    
    def _check_relevance(self, content: str) -> int:
        """
        Check content relevance to keywords with improved scoring.
        Returns a relevance score (0 = not relevant)
        """
        if not content or len(content) < 100:
            return 0
            
        content_lower = content.lower()
        base_score = 0
        
        # Score each keyword based on frequency and location
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            
            # Basic count
            count = content_lower.count(keyword_lower)
            base_score += count * 2
            
            # Check for exact matches (with word boundaries)
            exact_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            exact_matches = len(re.findall(exact_pattern, content_lower))
            base_score += exact_matches * 3
            
            # Check for keyword in first 500 characters (introduction)
            intro = content_lower[:500]
            if keyword_lower in intro:
                base_score += 10
                
            # Check for keyword in headers
            lines = content.split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                if keyword_lower in line_lower and len(line) < 100:
                    # Likely a header or title if short
                    base_score += 15
                    
        # Penalize very short content
        content_length = len(content)
        if content_length < 500:
            base_score = int(base_score * 0.7)
            
        # Bonus for longer, substantial content
        if content_length > 1000:
            base_score = int(base_score * 1.2)
        if content_length > 3000:
            base_score = int(base_score * 1.5)
            
        return base_score
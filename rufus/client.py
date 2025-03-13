import json
import logging
import os
import sys
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
from .ai_processor import AIContentProcessor
from .scraper import WebScraper
from .ai_processor import AIKeywordExtractor  # Add this import

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rufus')

class RufusClient:
    """Main client for the Rufus web scraping and content analysis tool"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Rufus client
        
        Args:
            api_key: OpenAI API key for content processing and advanced keyword extraction
                    If not provided, will look for OPENAI_API_KEY in environment variables
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No API key provided. Some features will be limited.")
            
        self.keyword_extractor = AIKeywordExtractor(self.api_key)
        self.ai_processor = AIContentProcessor(self.api_key)
        self.scraper = None
        
    async def scrape_with_cumulative_score(self, url: str, instructions: str, max_depth: int = 2, 
                                       min_score: int = 60, cumulative_score_threshold: int = 600) -> List[Dict]:
        """
        Scrape website starting from url based on instructions.
        Collects pages with relevance score >= min_score
        Stops crawling when the cumulative score of collected pages reaches cumulative_score_threshold
        
        Args:
            url: Starting URL for the scraping process
            instructions: Natural language instructions for the content to find
            max_depth: Maximum crawl depth (default: 2)
            min_score: Minimum relevance score for collecting pages (default: 60)
            cumulative_score_threshold: Cumulative score threshold to stop crawling (default: 600)
            
        Returns:
            List of collected pages with scores >= min_score
        """
        # Extract keywords using AI-powered method
        keywords = await self.keyword_extractor.extract_keywords(instructions)
        logger.info(f"Extracted keywords: {keywords}")
        
        # Initialize scraper with keywords
        self.scraper = WebScraper(keywords)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,  # Run in headless mode
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Rufus Web Scraper 1.0"
                )
                
                # Get pages with cumulative score criteria
                collected_pages = await self.scraper.crawl_with_score_criteria(
                    context=context,
                    start_url=url,
                    max_depth=max_depth,
                    min_score=min_score,
                    cumulative_score_threshold=cumulative_score_threshold
                )
                
                await browser.close()
                
                if not collected_pages:
                    logger.info("No relevant pages meeting score criteria found.")
                    return []
                    
                logger.info(f"Scraping completed. Collected {len(collected_pages)} relevant pages.")
                return collected_pages
                
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return []
    
    async def analyze(self, url: str, instructions: str, max_depth: int = 2, 
                     min_score: int = 60, cumulative_score_threshold: int = 600) -> Dict:
        """
        Complete analysis pipeline: Scrape, process, and generate a comprehensive report
        
        Args:
            url: Starting URL for the scraping process
            instructions: Natural language instructions for the content to find
            max_depth: Maximum crawl depth (default: 2)
            min_score: Minimum relevance score for collecting pages (default: 60)
            cumulative_score_threshold: Cumulative score threshold to stop crawling (default: 600)
            
        Returns:
            Comprehensive analysis results with summary and details
        """
        logger.info(f"Starting analysis of {url} with instructions: {instructions}")
        
        # Collect pages matching criteria
        collected_pages = await self.scrape_with_cumulative_score(
            url=url,
            instructions=instructions,
            max_depth=max_depth,
            min_score=min_score,
            cumulative_score_threshold=cumulative_score_threshold
        )
        
        if not collected_pages:
            logger.warning("No relevant pages found matching the criteria.")
            return {
                "query": instructions,
                "source_url": url,
                "collected_pages": 0,
                "summary": "No relevant content found. Try different keywords or a different starting URL.",
                "key_points": [],
                "details": []
            }
            
        logger.info(f"Processing {len(collected_pages)} pages with AI analysis...")
        
        # Process all collected pages with AI
        processed_results = []
        for page in collected_pages:
            logger.info(f"Processing page: {page['url']} (score: {page['relevance_score']})")
            
            # Create a focused prompt for this page
            focused_prompt = f"Based on the following content from {page['url']}, provide a detailed summary about {instructions}"
            
            processed = await self.ai_processor.process_content(page, focused_prompt)
            processed['source_url'] = page['url']
            processed['title'] = page.get('title', 'Untitled')
            processed['relevance_score'] = page['relevance_score']
            processed_results.append(processed)
        
        # Generate final comprehensive result
        final_result = {}
        if processed_results:
            logger.info("Generating final AI summary from all collected pages...")
            
            # Create combined content from all processed pages
            combined_data = {
                "content": "\n\n".join([
                    f"--- From {result['title']} ({result['source_url']}) (Score: {result['relevance_score']}) ---\n{result['summary']}"
                    for result in processed_results
                ])
            }
            
            # Generate comprehensive summary
            final_result = await self.ai_processor.process_content(
                combined_data,
                f"Based on the following information from multiple pages about {instructions}, provide a comprehensive analysis and summary:"
            )
        
        # Structure the output
        structured_output = {
            "query": instructions,
            "source_url": url,
            "collected_pages": len(processed_results),
            "summary": final_result.get('summary', ""),
            "key_points": final_result.get('key_points', []),
            "details": [
                {
                    "title": result.get("title", "Untitled"),
                    "url": result.get("source_url", ""),
                    "score": result.get("relevance_score", 0),
                    "content_summary": result.get("summary", ""),
                    "key_points": result.get("key_points", [])
                } for result in processed_results
            ]
        }
        
        logger.info("Analysis completed successfully")
        return structured_output

# Move these functions outside the class, making them separate functions in the module
async def run_rufus(url, query, api_key=None):
    """Run Rufus analysis and return results"""
    client = RufusClient(api_key)
    results = await client.analyze(url, query)
    return results

def cli_main():
    """Command-line interface main function"""
    if len(sys.argv) < 3:
        print("Usage: rufus <url> <query>")
        sys.exit(1)
        
    url = sys.argv[1]
    query = sys.argv[2]
    
    # Check for API key in environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: No OpenAI API key found. Set the OPENAI_API_KEY environment variable.")
        print("Some features may be limited.")
    
    # Run the analysis
    results = asyncio.run(run_rufus(url, query, api_key))
    
    # Print results
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    cli_main()
import pytest
import asyncio
from rufus.scraper import WebScraper
from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        scraper = WebScraper()
        
        # Example strategy (replace with a more meaningful one)
        strategy = {
            "content_selectors": "body",
            "keywords": ["example"]
        }
        
        results = await scraper.crawl(
            context=context,
            start_url="https://python.org",
            strategy=strategy,
            max_depth=1
        )
        
        assert len(results) > 0
        assert "example" in results[0]["content"].lower()
        
        await browser.close()

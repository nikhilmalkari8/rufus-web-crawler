# Rufus Web Crawler

An intelligent web scraper and content analyzer with AI-powered relevance scoring.

## Features

- AI-powered keyword extraction from natural language instructions
- Intelligent web crawling with relevance scoring
- Content analysis and summarization using OpenAI GPT models
- Score-based crawling with early stopping mechanism
- Comprehensive report generation

## Installation

```bash
pip install rufus-web-crawler
```

## Usage

### As a Python Library

```python
import asyncio
from rufus import RufusClient

async def main():
    # Initialize client (API key can be provided or set as OPENAI_API_KEY env variable)
    client = RufusClient(api_key="your-openai-api-key")
    
    # Run analysis
    result = await client.analyze(
        url="https://example.com",
        instructions="Find information about machine learning applications",
        max_depth=2,
        min_score=60,
        stop_score=100
    )
    
    # Print summary
    print(result['summary'])
    
    # Access detailed results
    for detail in result['details']:
        print(f"Page: {detail['title']} - {detail['url']}")
        print(f"Score: {detail['score']}")
        for point in detail['key_points']:
            print(f"  - {point}")

# Run the async function
asyncio.run(main())
```

### Command Line Interface

```bash
# Basic usage
rufus https://example.com "Find information about machine learning applications"

# With additional options
rufus https://example.com "Find information about machine learning" --depth 3 --min-score 70 --stop-score 95 --output results.json
```

## Requirements

- Python 3.7+
- OpenAI API key
- Playwright (automatically installed)
- NLTK (automatically installed)

## License

MIT
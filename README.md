# Rufus: Web Scraping & AI Content Analysis

Rufus is an advanced web scraping and content analysis tool that uses AI to intelligently crawl websites, extract relevant content, and generate comprehensive summaries based on natural language instructions.

## Features

- **AI-Powered Keyword Extraction**: Converts natural language instructions into targeted keywords for intelligent scraping
- **Smart Web Crawling**: Scores pages based on content relevance to focus only on valuable information
- **Cumulative Scoring System**: Stops crawling when sufficient relevant content has been collected
- **AI Content Processing**: Generates summaries, key points, and insights from collected content
- **Structured Output**: Returns well-organized results that are easy to use in downstream applications

## Installation

```bash
# Install package locally
pip install -e .
pip install rufus-web-crawler

# Or clone the repository
git clone https://github.com/yourusername/rufus.git
cd rufus

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Requirements

- Python 3.7+
- Playwright
- OpenAI API key (for advanced features)
- NLTK (with punkt and stopwords datasets)

## Usage

### Working Example

```python
import asyncio
import json
import sys
from rufus.client import RufusClient

async def main():
    url = "https://www.dennys.com"
    instructions = "get the details of burgers"
    client = RufusClient()
    min_score_threshold = 60
    stop_score_threshold = 100
    
    print(f"Starting scraping of {url} with instructions: {instructions}")
    print(f"Will collect pages with score >= {min_score_threshold} and stop at {stop_score_threshold}")
    
    collected_pages = await client.scrape_with_score_criteria(
        url=url,
        instructions=instructions,
        max_depth=2,
        min_score=min_score_threshold,
        stop_score=stop_score_threshold
    )
    
    if not collected_pages:
        print("No relevant pages found matching the criteria.")
        return
        
    print(f"Collected {len(collected_pages)} pages with scores between {min_score_threshold} and {stop_score_threshold}+")
    
    processed_results = []
    for page in collected_pages:
        print(f"Processing page: {page['url']} (score: {page['relevance_score']})")
        
        focused_prompt = f"Based on the following content from {page['url']}, {instructions}"
        processed = await client.ai_processor.process_content(page, focused_prompt)
        processed['source_url'] = page['url']
        processed['relevance_score'] = page['relevance_score']
        processed_results.append(processed)
    
    final_result = {}
    if processed_results:
        print("Generating final AI summary from all collected pages...")
        
        combined_data = {
            "content": "\n\n".join([
                f"--- From {result['source_url']} (Score: {result['relevance_score']}) ---\n{result['summary']}"
                for result in processed_results
            ])
        }
        
        final_result = await client.ai_processor.process_content(
            combined_data,
            f"Based on the following information from multiple pages about {instructions}, provide a comprehensive summary:"
        )
        
        structured_output = {
            "query": instructions,
            "source_url": url,
            "collected_pages": len(processed_results),
            "summary": final_result.get('summary', ""),
            "key_points": final_result.get('key_points', []),
            "details": [
                {
                    "url": result.get("source_url", ""),
                    "score": result.get("relevance_score", 0),
                    "content_summary": result.get("summary", ""),
                    "key_points": result.get("key_points", [])
                } for result in processed_results
            ]
        }
        
        output_file = "scraping_results.json"
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(structured_output, json_file, indent=4, ensure_ascii=False)
        
        print(f"\nResults saved to '{output_file}'.")
        print(json.dumps(structured_output, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
```

### Command Line Interface

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-openai-api-key

# Run the scraper
python -m rufus "https://example.com" "Find information about renewable energy technologies"
```

### Customizing Scraping Parameters

You can customize the scraping behavior by adjusting the parameters in both the `analyze()` and `scrape_with_cumulative_score()` methods:

```python
# For direct scraping
results = await client.scrape_with_cumulative_score(
    url="https://example.com",
    instructions="Find information about machine learning applications",
    min_score=75,  # Only collect pages with score >= 75
    cumulative_score_threshold=800  # Stop when cumulative score reaches 800
)

# Or through the analyze method
results = await client.analyze(
    url="https://example.com",
    instructions="Find information about machine learning applications",
    min_score=75,  # Only collect pages with score >= 75
    cumulative_score_threshold=800  # Stop when cumulative score reaches 800
)
```

These methods are found in the `RufusClient` class (`rufus_client.py` or the main module file). You can call them directly after initializing the client as shown above.

## How It Works

1. **Keyword Extraction**: Uses OpenAI's GPT models (or falls back to NLTK) to extract relevant keywords from your instructions
2. **Website Crawling**: Starts from the provided URL and follows links, prioritizing same-domain links
3. **Content Scoring**: Evaluates each page for relevance based on the extracted keywords
4. **Targeted Collection**: Collects pages that meet the minimum relevance score
5. **Early Stopping**: Stops crawling once enough relevant content has been collected (based on cumulative score)
6. **AI Analysis**: Processes collected pages with OpenAI's GPT models to generate summaries and key points
7. **Structured Output**: Returns results in a well-organized format

## Scoring System

Rufus uses a sophisticated scoring system to evaluate page relevance:

- Higher scores for exact keyword matches
- Bonus points for keywords in document titles and introductions
- Length-based score adjustments (longer, more detailed content gets higher scores)
- Cumulative scoring to ensure comprehensive coverage of the topic

### Scoring Parameters

- `min_score` (default: 60): The minimum relevance score a page must have to be collected. Pages with scores below this threshold are ignored.
- `cumulative_score_threshold` (default: 600): The total combined score of all collected pages that triggers the crawler to stop. Once the sum of scores from collected pages reaches or exceeds this value, the crawler determines it has found enough relevant content.

## Configuration Options

### RufusClient

```python
client = RufusClient(
    api_key="your-openai-api-key"  # Optional, can use OPENAI_API_KEY environment variable
)
```

### Analyze Method

```python
results = await client.analyze(
    url="https://example.com",           # Starting URL
    instructions="...",                  # Natural language instructions
    max_depth=2,                         # Maximum crawl depth
    min_score=60,                        # Minimum page relevance score
    cumulative_score_threshold=600       # Total relevance score to collect
)
```

## Output Structure

```json
{
  "query": "Original instructions",
  "source_url": "Starting URL",
  "collected_pages": 5,
  "summary": "Comprehensive summary of all collected content",
  "key_points": ["Key point 1", "Key point 2", ...],
  "details": [
    {
      "title": "Page Title",
      "url": "Page URL",
      "score": 85,
      "content_summary": "Summary of this specific page",
      "key_points": ["Page-specific key point 1", "Page-specific key point 2", ...]
    },
    ...
  ]
}
```

## Limitations

- Requires an OpenAI API key for advanced features (will fall back to simpler methods without one)
- Some websites may block or rate-limit scraping attempts
- JavaScript-heavy websites may not be fully accessible

## License

[MIT License](LICENSE)

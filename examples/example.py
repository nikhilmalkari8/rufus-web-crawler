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

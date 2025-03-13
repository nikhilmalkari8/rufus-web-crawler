import json
from typing import List, Dict

def format_output(data: List[Dict]) -> List[Dict]:
    """Formats the output data into a clean JSON structure."""
    return [
        {
            "summary": item.get("summary", "No summary available"),
            "key_points": item.get("key_points", []),
            "source_urls": item.get("source_urls", [])
        }
        for item in data
    ]

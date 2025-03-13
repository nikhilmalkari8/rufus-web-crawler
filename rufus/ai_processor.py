import json
import os
import logging
from typing import List, Dict, Any, Optional
import openai
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rufus')

# Ensure NLTK data is downloaded
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK data: {e}. Using fallback methods.")

class AIKeywordExtractor:
    """Uses AI models to extract relevant keywords from user instructions"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the keyword extractor with an optional API key"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Advanced keyword extraction will be limited.")
    
    async def extract_keywords(self, instructions: str) -> List[str]:
        """Extract keywords using GPT model for more intelligent analysis"""
        if not self.api_key:
            logger.warning("No API key available for GPT keyword extraction. Using fallback method.")
            return self._fallback_keyword_extraction(instructions)
            
        try:
            # Configure OpenAI with the API key
            openai.api_key = self.api_key
            
            # Call GPT to extract keywords
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Using GPT-4 for better understanding
                messages=[
                    {"role": "system", "content": "You are a keyword extraction specialist. Extract the most relevant search keywords from the given instructions. Focus on terms that would be useful for web crawling and content relevance matching. Return only a JSON array of the keywords, nothing else."},
                    {"role": "user", "content": instructions}
                ],
                max_tokens=150,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Extract keywords from response
            result = json.loads(response.choices[0].message.content)
            keywords = result.get("keywords", [])
            
            if not keywords:
                logger.warning("GPT returned no keywords. Using fallback method.")
                return self._fallback_keyword_extraction(instructions)
                
            logger.info(f"GPT extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"GPT keyword extraction failed: {e}")
            return self._fallback_keyword_extraction(instructions)
    
    def _fallback_keyword_extraction(self, instructions: str) -> List[str]:
        """Fallback method using NLTK for keyword extraction"""
        try:
            # Try to use NLTK for sophisticated keyword extraction
            stop_words = set(stopwords.words('english'))
            words = word_tokenize(instructions.lower())
            
            # Extract phrases related to the query
            phrases = []
            current_phrase = []
            
            for word in words:
                if word.lower() not in stop_words and word.isalpha():
                    current_phrase.append(word)
                elif current_phrase:
                    if len(current_phrase) > 1:
                        phrases.append(" ".join(current_phrase))
                    else:
                        phrases.append(current_phrase[0])
                    current_phrase = []
            
            if current_phrase:
                if len(current_phrase) > 1:
                    phrases.append(" ".join(current_phrase))
                else:
                    phrases.append(current_phrase[0])
            
            # Extract individual keywords too
            stemmer = PorterStemmer()
            individual_keywords = [stemmer.stem(word.lower()) for word in words 
                                  if word.lower() not in stop_words and word.isalpha()]
            
            # Combine phrases and individual keywords
            all_keywords = phrases + individual_keywords
            
            # For "get details of admissions", we want to make sure "admissions" is included
            query_topic = re.search(r'(?:details|information|info)\s+(?:of|about|on)\s+(\w+)', instructions.lower())
            if query_topic and query_topic.group(1) not in all_keywords:
                all_keywords.append(query_topic.group(1))
                
            # Remove duplicates but preserve order
            seen = set()
            keywords = [x for x in all_keywords if not (x in seen or seen.add(x))]
            
            logger.info(f"Fallback extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Fallback keyword extraction failed: {e}")
            # Super simple fallback
            words = instructions.lower().split()
            keywords = [word for word in words if len(word) > 3]
            logger.info(f"Simple extracted keywords: {keywords}")
            return keywords


class AIContentProcessor:
    """Process web content using AI models to generate summaries and insights"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with an OpenAI API key"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("No OpenAI API key provided for content processing.")
        else:
            openai.api_key = self.api_key
        
    async def process_content(self, content_data: Dict, instructions: str) -> Dict:
        """Process website content with AI model based on instructions"""
        if not content_data or "content" not in content_data:
            return {"summary": "No content found", "key_points": [], "source_url": None}
            
        if not self.api_key:
            return {
                "summary": "API key required for content processing",
                "key_points": [],
                "source_url": content_data.get('url')
            }
            
        try:
            # Chunk the content if it's too large
            content = content_data["content"]
            chunks = self._chunk_content(content)
            
            results = []
            
            for i, chunk in enumerate(chunks):
                # Adjust prompt for chunk information
                chunk_prompt = instructions
                if len(chunks) > 1:
                    chunk_prompt = f"{instructions} (Content part {i+1}/{len(chunks)})"
                
                try:
                    # Use the chat completions API
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that summarizes web content accurately and concisely, extracting the most relevant information based on the user's instructions."},
                            {"role": "user", "content": f"{chunk_prompt}\n\n{chunk}"}
                        ],
                        max_tokens=800,
                        temperature=0.3
                    )
                    
                    text = response.choices[0].message.content.strip()
                    results.append(text)
                    
                except Exception as e:
                    logger.error(f"Error processing content chunk {i+1}: {e}")
                    results.append(f"Error processing content: {str(e)}")
            
            # Combine the results
            combined_result = "\n\n".join(results)
            
            # Extract key points
            key_points = self._extract_key_points(combined_result)
            
            return {
                "summary": combined_result,
                "key_points": key_points,
                "source_url": content_data.get('url', 'No URL provided'),
                "title": content_data.get('title', 'Untitled')
            }
            
        except Exception as e:
            logger.error(f"Failed to process content: {e}")
            return {"error": f"Failed to process content: {str(e)}"}
            
    def _chunk_content(self, content: str, max_length: int = 4000) -> List[str]:
        """Split content into manageable chunks for the AI model"""
        if len(content) <= max_length:
            return [content]
            
        # Split by paragraphs to maintain context
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            if current_length + para_length > max_length and current_chunk:
                # Current chunk is full, start a new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                # Add paragraph to current chunk
                current_chunk.append(para)
                current_length += para_length
                
        # Add the last chunk if there's anything left
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks
        
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from the AI-generated summary"""
        points = []
        
        # Look for bullet points or numbered lists
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Check for bullet points or numbering
            if line.startswith(('•', '-', '*', '1.', '2.', '3.')) and len(line) > 5:
                # Clean up the point
                point = line.lstrip('•-*123456789. ')
                points.append(point)
                
        # If no bullet points found, try to make our own from sentences
        if not points:
            sentences = text.split('. ')
            points = [s.strip() + '.' for s in sentences if len(s) > 20 and len(s) < 200][:5]
            
        return points[:10]  # Limit to 10 key points
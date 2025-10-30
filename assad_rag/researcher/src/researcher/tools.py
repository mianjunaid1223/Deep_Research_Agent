"""Tools for web search and content reading."""
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

def search_web(query: str) -> List[Dict[str, str]]:
    """Perform a web search using Google Custom Search API."""
    try:
        from googleapiclient.discovery import build
        
        # Get API credentials from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        search_engine_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not search_engine_id:
            raise ValueError("Missing Google API credentials")
        
        # Create search service
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Perform search
        result = service.cse().list(q=query, cx=search_engine_id, num=5).execute()
        
        # Extract search results
        search_results = []
        if "items" in result:
            for item in result["items"]:
                search_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
        
        return search_results
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def get_search_links(query: str) -> list:
    """Get scientific research-focused search results."""
    try:
        # Create search service
        from googleapiclient.discovery import build
        
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            print("Missing Google API credentials")
            return []
            
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Add scientific focus to the query
        scientific_query = f"{query} (site:.edu OR site:.gov OR site:nature.com OR site:science.org OR site:sciencedirect.com OR site:ncbi.nlm.nih.gov)"
        
        # Execute search
        result = service.cse().list(
            q=scientific_query,
            cx=cse_id,
            num=10  # Request more results
        ).execute()
        
        # Extract URLs
        links = []
        if "items" in result:
            for item in result["items"]:
                url = item.get("link", "")
                # Prioritize scientific domains
                if any(domain in url.lower() for domain in [
                    '.edu', '.gov', 'nature.com', 'science.org', 
                    'sciencedirect.com', 'ncbi.nlm.nih.gov'
                ]):
                    links.append(url)
        
        # Take top 5 unique links
        unique_links = list(dict.fromkeys(links))[:5]
        
        print(f"Found {len(unique_links)} scientific sources")
        if not unique_links:
            print("No scientific sources found, trying general search...")
            # Fallback to general search if no scientific sources found
            result = service.cse().list(
                q=query,
                cx=cse_id,
                num=5
            ).execute()
            
            if "items" in result:
                unique_links = [item.get("link", "") for item in result["items"]]
                print(f"Found {len(unique_links)} general sources")
        
        return unique_links
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def web_scrape_for_llm(url: str, retries=2, delay=1) -> str:
    """Read content from a webpage with retries."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                    element.decompose()
                
                # Get text content
                text = soup.get_text(separator=' ', strip=True)
                
                # Clean up text
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()
                
                # Truncate if too long
                if len(text) > 10000:
                    text = text[:10000] + "..."
                
                if text:
                    return text
                    
            except requests.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                return f"Error: Failed to fetch {url}: {str(e)}"
                
        return f"Error: No content found for {url}"
        
    except Exception as e:
        return f"Error: Failed to process {url}: {str(e)}"

def read_url_content(url: str) -> str:
    """Read content from a URL."""
    return web_scrape_for_llm(url)

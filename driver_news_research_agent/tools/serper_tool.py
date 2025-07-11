from crewai.tools import BaseTool
from schemas.news_fetch import NewsArticle
import os
import requests
from datetime import datetime
import re

class SerperNewsTool(BaseTool):
    name = "SerperNewsTool"
    description = "Fetch latest news articles using Serper.dev API for specific F1 sources"

    def _run(self, query: str) -> list[NewsArticle]:
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }
        
        response = requests.post("https://google.serper.dev/news", headers=headers, json={"q": query})
        data = response.json()

        articles = []
        for item in data.get("news", [])[:5]:  # Get up to 5 articles
            # Extract source from query or use source from API
            source = "Unknown"
            if "site:" in query:
                source = query.split("site:")[1].split()[0]
            elif "source" in item:
                source = item["source"]
            
            # Handle relative time formats
            date_str = item.get("date", "")
            try:
                if "ago" in date_str:
                    # For relative dates, use current time
                    published_at = datetime.now()
                else:
                    from dateutil.parser import parse
                    published_at = parse(date_str)
            except:
                published_at = datetime.now()
            
            articles.append(NewsArticle(
                title=item.get("title", ""),
                description=item.get("snippet", ""),
                source=source,
                published_at=published_at
            ))
        return articles

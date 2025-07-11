from pydantic import BaseModel
from typing import List
from datetime import datetime

class NewsArticle(BaseModel):
    title: str
    description: str
    source: str
    published_at: datetime

class NewsFetchOutput(BaseModel):
    articles: List[NewsArticle]

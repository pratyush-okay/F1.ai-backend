#!/usr/bin/env python3
"""
CrewAI News Fetcher for F1 Drivers
==================================

This script uses CrewAI to fetch news articles about F1 drivers from 5 trusted sports sources:
- ESPN F1
- Fox Sports  
- BBC Sport
- Sky Sports F1
- Autosport
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Type
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# CrewAI imports
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool

# Local imports
from driver_news_research_agent.schemas.news_fetch import NewsFetchOutput


def setup_environment():
    """Setup project directories and environment variables"""
    print("🔧 Setting up environment...")
    
    # Create project structure
    os.makedirs("config", exist_ok=True)
    os.makedirs("schemas", exist_ok=True)
    os.makedirs("tools", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    
    # Load environment variables
    load_dotenv()
    serper_api_key = os.getenv("SERPER_API_KEY")
    
    if not serper_api_key:
        raise ValueError("Please set SERPER_API_KEY in your .env file")
    
    print("✅ Environment setup complete!")
    return serper_api_key


class SerperSearchInput(BaseModel):
    """Input schema for Serper news search."""
    query: str = Field(..., description="Search query string, can include site: restrictions for F1 sources")


class SerperNewsTool(BaseTool):
    name: str = "serper_news_search"
    description: str = (
        "Search for latest F1 news articles using Serper.dev API. "
        "Can search specific sites like ESPN F1, Fox Sports, BBC Sport, Sky Sports F1, and Autosport. "
        "Use 'site:domain.com' in query to restrict to specific sources."
    )
    args_schema: Type[BaseModel] = SerperSearchInput

    def _run(self, query: str) -> str:
        """
        Fetch latest news articles using Serper.dev API for F1 sources.
        
        Args:
            query: Search query string, can include site: restrictions
            
        Returns:
            JSON string containing news articles with title, description, source, and published date
        """
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post("https://google.serper.dev/news", headers=headers, json={"q": query})
            data = response.json()

            articles = []
            for item in data.get("news", [])[:5]:  # Get up to 5 articles
                # Extract source from query or use source from API
                source = "Unknown"
                if "site:" in query:
                    source_part = query.split("site:")[1].split()[0]
                    if "espn.com" in source_part:
                        source = "ESPN F1"
                    elif "foxsports.com" in source_part:
                        source = "Fox Sports"
                    elif "bbc.com" in source_part:
                        source = "BBC Sport"
                    elif "skysports.com" in source_part:
                        source = "Sky Sports F1"
                    elif "autosport.com" in source_part:
                        source = "Autosport"
                    else:
                        source = source_part
                elif "source" in item:
                    source = item["source"]
                
                # Handle relative time formats
                date_str = item.get("date", "")
                try:
                    if "ago" in date_str:
                        published_at = datetime.now().isoformat()
                    else:
                        try:
                            from dateutil.parser import parse
                            published_at = parse(date_str).isoformat()
                        except ImportError:
                            published_at = datetime.now().isoformat()
                except:
                    published_at = datetime.now().isoformat()
                
                articles.append({
                    "title": item.get("title", ""),
                    "description": item.get("snippet", ""),
                    "source": source,
                    "published_at": published_at
                })
            
            return json.dumps({"articles": articles, "success": True})
        except Exception as e:
            return json.dumps({"error": str(e), "success": False})


# Create the tool instance
serper_tool = SerperNewsTool()

# LLM configuration
gpt_4o = LLM(model="gpt-4o")


@CrewBase
class F1NewsCrew():
    """F1 News Fetcher crew using modern CrewAI patterns"""

    # YAML configuration files
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def news_fetcher_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['news_fetcher_agent'],
            verbose=True,
            llm=gpt_4o,
            tools=[serper_tool]
        )

    @agent  
    def news_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['news_analyzer_agent'],
            verbose=True,
            llm=gpt_4o
        )

    @task
    def fetch_news_articles(self) -> Task:
        return Task(
            config=self.tasks_config['fetch_news_articles'],
            agent=self.news_fetcher_agent(),
            tools=[serper_tool],
            output_pydantic=NewsFetchOutput
        )

    @task
    def analyze_news_sentiment(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_news_sentiment'],
            agent=self.news_analyzer_agent(),
            context=[self.fetch_news_articles()],
            output_file='outputs/f1_news_analysis.json'
        )

    @crew
    def f1_news_crew(self) -> Crew:
        """Creates the F1 News crew"""
        return Crew(
            agents=[
                self.news_fetcher_agent(),
                self.news_analyzer_agent()
            ],
            tasks=[
                self.fetch_news_articles(),
                self.analyze_news_sentiment()
            ],
            process=Process.sequential,
            verbose=True
        )


def run_f1_news_analysis(driver_name: str = "Max Verstappen"):
    """
    Run the F1 news analysis for a specific driver
    
    Args:
        driver_name: Name of the F1 driver to analyze
    """
    print(f"🚀 Initializing F1 News Crew for {driver_name}...")
    
    try:
        # Create crew instance
        f1_crew_instance = F1NewsCrew()
        
        # Get the configured crew
        crew = f1_crew_instance.f1_news_crew()
        
        print("📰 Starting news analysis workflow...")
        print("🔍 Will search across ESPN F1, Fox Sports, BBC Sport, Sky Sports F1, and Autosport...")
        
        # Run the crew with inputs
        inputs = {
            'driver_name': driver_name,
            'search_sources': [
                'site:espn.com/f1',
                'site:foxsports.com', 
                'site:bbc.com/sport',
                'site:skysports.com/f1',
                'site:autosport.com'
            ]
        }
        
        result = crew.kickoff(inputs=inputs)
        
        print("\n📊 Crew execution completed!")
        print("=" * 50)
        
        if result:
            print("✅ Results generated successfully!")
            print(f"📄 Check outputs/f1_news_analysis.json for detailed analysis")
            
            # Display basic info if result has articles
            if hasattr(result, 'articles') and result.articles:
                print(f"\n📰 Found {len(result.articles)} articles")
                for i, article in enumerate(result.articles[:3], 1):  # Show first 3
                    print(f"\n{i}. {article.title[:80]}...")
                    print(f"   Source: {article.source}")
            else:
                print("\n📋 Result:")
                print(str(result)[:200] + "..." if len(str(result)) > 200 else str(result))
        else:
            print("⚠️ No results returned")
            
        return result
        
    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check SERPER_API_KEY is set in .env file") 
        print("2. Verify YAML config files exist in config/")
        print("3. Ensure internet connection is available")
        print("4. Make sure schemas/news_fetch.py exists with NewsFetchOutput")
        return None


def main():
    """Main function to run the F1 news analysis"""
    try:
        # Setup environment
        setup_environment()
        
        # Get driver name from command line argument or use default
        driver_name = sys.argv[1] if len(sys.argv) > 1 else "Max Verstappen"
        
        print(f"🏎️ F1 News Analysis for {driver_name}")
        print("=" * 50)
        
        # Run the analysis
        result = run_f1_news_analysis(driver_name)
        
        if result:
            print(f"\n🎉 Analysis complete for {driver_name}!")
        else:
            print(f"\n❌ Analysis failed for {driver_name}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
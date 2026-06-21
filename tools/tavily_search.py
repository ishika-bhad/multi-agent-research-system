import os
from dotenv import dotenv_values
from langchain_tavily import TavilySearch

config = dotenv_values(".env")

os.environ["TAVILY_API_KEY"] = config["TAVILY_API_KEY"]

searchTool = TavilySearch(
    max_results=3,
    include_raw_content=True,
    include_answer=True
)
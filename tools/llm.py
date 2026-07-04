import os
from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic

config = dotenv_values(".env")

os.environ["ANTHROPIC_API_KEY"] = config["ANTHROPIC_API_KEY"]

llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    temperature=0.3,
    max_tokens=8192,
)
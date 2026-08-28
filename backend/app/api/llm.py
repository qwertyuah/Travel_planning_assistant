import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.1,
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

from langchain_openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from utils.logger import setup_colored_logger

setup_colored_logger()

load_dotenv()

llm = OpenAI()

prompt = PromptTemplate.from_template("How to say {input} in {output_language}:\n")

chain = prompt | llm
result = chain.invoke(
    {
        "output_language": "German",
        "input": "I love programming.",
    }
)

print(result)
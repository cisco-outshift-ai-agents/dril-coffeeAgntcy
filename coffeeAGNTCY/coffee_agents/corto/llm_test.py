from dotenv import load_dotenv

load_dotenv()

from langchain_nvidia_ai_endpoints import ChatNVIDIA

llm = ChatNVIDIA(model="openai/gpt-oss-20b")

response = llm.predict("Can you tell me a joke?")
print(response)
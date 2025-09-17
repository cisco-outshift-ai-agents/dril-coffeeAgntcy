from dotenv import load_dotenv

load_dotenv()

from langchain_nvidia_ai_endpoints import ChatNVIDIA

llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")

response = llm.predict("Can you tell me a joke?")
print(response)
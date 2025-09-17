import os

from langchain_nvidia_ai_endpoints import ChatNVIDIA

os.environ["NVIDIA_API_KEY"] = "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"

llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")

response = llm.predict("Can you tell me a joke?")
print(response)
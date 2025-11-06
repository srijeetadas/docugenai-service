from openai import OpenAI
client = OpenAI()
print(client.embeddings.create(model="text-embedding-3-small", input="Hello world"))
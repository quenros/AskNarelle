import os

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

class EmbeddingService:
    def __init__(
            self,
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            embedding_model=os.environ.get("EMBEDDING_MODEL")
    ):
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
        self.embedding_model = embedding_model


    def embed_query(self, user_prompt):
        response = self.client.embeddings.create(input=user_prompt, model=self.embedding_model)
        return response.data[0].embedding

if __name__ == "__main__":
    embedding_service = EmbeddingService()
    print(embedding_service.embed_query(user_prompt="hi"))
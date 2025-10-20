import os

from dotenv import load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI


from langchain_core.prompts import PromptTemplate
from openai import AsyncAzureOpenAI

from chatservice.repository import ChatDatabaseService
from chatservice.model import ChatHistory
from chatservice.utils import weighted_reciprocal_rank
from loggingConfig import logger
from utils import process_file, get_prompt_template, get_prompt_template_naive, prompt_template_test

load_dotenv()

class ChatService:
    """
    ChatService is a wrapper class of AsyncAzureOpenAI used for generating responses from Azure OpenAI LLM.
    It provides the ability to add system message, grounding text, and a generic prompt template.

    Args:
        azure_endpoint (str): Azure OpenAI Endpoint. Example: https://<YOUR_RESOURCE_NAME>.openai.azure.com/. Required.
        api_key (str): Azure OpenAI API Key. Required.
        deployment_name (str): Azure OpenAI Deployment Name. Example: gpt-4o-mini. Required.
        prompt_template_fp (str): Filepath to prompt template to be used in chatbot prompt. Default: "prompt_template.txt".
        temperature (float): Chatbot Temperature. Default: 0.
        embedding_model (str): Embedding Model. Default: "all-MiniLM-L6-v2".
    """
    def __init__(
            self,
            azure_endpoint: str = os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key: str = os.environ.get("AZURE_OPENAI_API_KEY"),
            deployment_name: str = os.environ.get("YOUR_DEPLOYMENT_NAME"),
            api_version : str = os.environ.get("OPENAI_API_VERSION"),
            temperature: float=0,
    ):
        self.azure_endpoint = azure_endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.client = self.initiate_client()
        try:
            self.prompt_template = get_prompt_template()
        except Exception as e:
            print(e)
            self.prompt_template = ""
        self.chat_model = AzureChatOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            azure_deployment=deployment_name,
            temperature=temperature
        )
        self.chat_db = ChatDatabaseService()

    def initiate_client(self):
        """
        Initialises a AsyncAzureOpenAI instance to interact with Azure OpenAI services.
        Uses provided Azure endpoint, API key, and API version.
        If an error occurs during initialization, the Azure endpoint and the exception are printed for debugging.

        Returns:
            AsyncAzureOpenAI: An initialised instance of the AsyncAzureOpenAI class.

        Raises:
            Exception: For any errors that occur during initialization.
        """
        try:
            return AsyncAzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        except Exception as ex:
            print("something happened here")
            print(ex)

    def generate_video_prompt_response(self, retrieval_results, user_input, previous_messages=None):
        """
        Generate response based on user prompt and selected video.

        Args:
            user_prompt (str): User prompt to query chatbot. Required.
            video_id (str): Video ID of the video selected. Required.
            :param previous_messages:
            :param user_input:
            :param retrieval_results:
        """
        if previous_messages is None:
            previous_messages = []
        try:
            formatted_history = "\n".join(
                [f"User: {msg.user_input}\nAssistant: {msg.assistant_response}" for msg in previous_messages])

            prompt = PromptTemplate(
                template=get_prompt_template(),
                input_variables=["context", "input", "history"]
            )

            context = retrieval_results

            combine_docs_chain = create_stuff_documents_chain(self.chat_model, prompt)

            # Generate the full prompt with context and input
            final_prompt = prompt.format(context=context, input=user_input, history=formatted_history)

            # Save the prompt to a file
            process_file(fp="generated_prompt.txt", mode="w", content=final_prompt)

            # Return the response
            return combine_docs_chain.invoke({
                "context": retrieval_results,
                "input": user_input,
                "history": formatted_history
            })
        except Exception as ex:
            print("Something happened: ", ex)
            return ex

    # Semantic Search on Uncleaned results
    def retrieve_results_prompt_naive(self, video_id, message, top_n: int = 5):
        docs_semantic = self.chat_db.retrieve_results_prompt_semantic(video_id, message)[:top_n]
        logger.info(list(docs_semantic))
        retrieval_results = [Document(page_content=doc['textContent']) for doc in docs_semantic]
        return retrieval_results, [doc['textContent'] for doc in docs_semantic]

    def retrieve_results_prompt_clean_naive(self, video_id, message, top_n: int = 5):
        docs_semantic = self.chat_db.retrieve_results_prompt_semantic_v2(video_id, message)[:top_n]
        logger.info(list(docs_semantic))
        retrieval_results = [Document(page_content=doc['textContent']) for doc in docs_semantic]
        return retrieval_results, [doc['textContent'] for doc in docs_semantic]

    # Text + Semantic Search on Uncleaned results
    def retrieve_results_prompt(self, video_id, message, top_n: int = 5):
        docs_semantic = self.chat_db.retrieve_results_prompt_semantic(video_id, message)
        docs_text = self.chat_db.retrieve_results_prompt_text(video_id, message)
        logger.info(list(docs_semantic))
        logger.info(list(docs_text))
        doc_lists = [docs_semantic, docs_text]
        # Enforce that retrieved docs are the same form for each list in retriever_docs
        for i in range(len(doc_lists)):
            doc_lists[i] = [
                {"_id": str(doc["_id"]), "text": doc["textContent"], "score": doc["score"]}
                for doc in doc_lists[i]]
        fused_documents = weighted_reciprocal_rank(doc_lists)[:top_n]
        retrieval_results = [Document(page_content=doc['text']) for doc in fused_documents]
        print(retrieval_results)
        return retrieval_results, [doc['text'] for doc in fused_documents]

    # Text + Semantic Search on Cleaned results
    def retrieve_results_prompt_clean(self, video_id, message, top_n: int=5):
        docs_semantic = self.chat_db.retrieve_results_prompt_semantic_v2(video_id, message)
        docs_text = self.chat_db.retrieve_results_prompt_text_v2(video_id, message)
        logger.info(list(docs_semantic))
        logger.info(list(docs_text))
        doc_lists = [docs_semantic, docs_text]
        # Enforce that retrieved docs are the same form for each list in retriever_docs
        for i in range(len(doc_lists)):
            doc_lists[i] = [
                {"_id": str(doc["_id"]), "text": doc["textContent"], "score": doc["score"]}
                for doc in doc_lists[i]]
        fused_documents = weighted_reciprocal_rank(doc_lists)[:top_n]
        retrieval_results = [Document(page_content=doc['text']) for doc in fused_documents]
        print(retrieval_results)
        return retrieval_results, [doc['text'] for doc in fused_documents]
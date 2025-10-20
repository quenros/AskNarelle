import os
import re
from typing import List, Any, Mapping

import numpy as np
from bson import ObjectId
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI

from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter
from openai import AsyncAzureOpenAI

from brokerservice.model import CourseDetails
from loggingConfig import logger
from transcriptservice.repository import TranscriptRepositoryService
from utils import convert_seconds_to_mm_ss, process_file, get_prompt_template, get_clean_prompt_template, \
    timestamp_to_seconds, seconds_to_timestamp


def break_transcript_to_chunks(transcript, max_length=10000):
    chunks = []
    items = re.findall(r'\[\d{1,2}:\d{2}:\d{2}.\d{1,2}] [^\[]+', transcript)
    current_size = 0
    current_items = []
    for item in items:
        current_size += len(item)
        current_items.append(item)
        if current_size > max_length:
            chunks.append(''.join(current_items))
            current_size = 0
            current_items = []
    if current_items:
        chunks.append(''.join(current_items))
    return chunks

class TranscriptService:
    """
    OpenAIService is a wrapper class of AsyncAzureOpenAI used for generating responses from Azure OpenAI LLM.
    It provides the ability to add system message, grounding text, and a generic prompt template.

    Args:
        azure_endpoint (str): Azure OpenAI Endpoint. Example: https://<YOUR_RESOURCE_NAME>.openai.azure.com/. Required.
        api_key (str): Azure OpenAI API Key. Required.
        deployment_name (str): Azure OpenAI Deployment Name. Example: gpt-4o-mini. Required.
        database_service (AzureDatabaseService): Instance of AzureDatabaseService class. Required.
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
            transcript_db: TranscriptRepositoryService = TranscriptRepositoryService(),
    ):
        self.azure_endpoint = azure_endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.transcript_db = transcript_db
        self.client = self.initiate_client()
        try:
            self.prompt_template = get_clean_prompt_template()
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
            print(ex)

    def generate_clean_transcript(self, transcript: str, course_description: str, video_description: str):
        try:
            prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["course description", "video description", "context"]
            )

            combine_docs_chain = create_stuff_documents_chain(self.chat_model, prompt)

            return combine_docs_chain.invoke({
                "course description": course_description,
                "video description": video_description,
                "context": [Document(page_content=transcript)]
            })
        except Exception as ex:
            print(ex)
            return ex

    def trigger_transcript_cleaning(self, video_id: ObjectId, course: dict, video_description: str):
        transcript_object = self.transcript_db.find_transcript_given_video_reference_id(video_id)
        transcript = transcript_object["transcript_timestamp"]
        transcript_chunks = break_transcript_to_chunks(transcript)
        course_outline = " ".join([course["course_code"], course["course_name"], course["course_description"]])
        responses_clean = []
        for transcript_chunk in transcript_chunks:
            response_clean = self.generate_clean_transcript(
                transcript_chunk, course_outline, video_description)
            responses_clean.append(response_clean.replace("\n", "").replace("\r", ""))
        responses_clean = "".join(responses_clean)
        self.transcript_db.update_transcript(video_id, responses_clean)
        return responses_clean

    def map_insights_to_transcript(self, insight, video_id):
        transcript_list = insight["videos"][0]["insights"]["transcript"]
        document = {
            "phrases": [
                {
                    "start": phrase["instances"][0]["adjustedStart"],
                    "end": phrase["instances"][0]["adjustedEnd"],
                    "phrase": phrase["text"]
                } for phrase in transcript_list
            ]
        }

        transcript_timestamp = ""
        transcript_raw = ""
        for phrase in transcript_list:
            transcript_timestamp += "[" + phrase["instances"][0]["adjustedStart"] + "] "
            transcript_timestamp += phrase["text"] + " "
            transcript_raw += phrase["text"] + " "
        document["transcript_timestamp"] = transcript_timestamp.strip()
        document["transcript"] = transcript_raw.strip()
        document["video_reference_id"] = video_id

        self.transcript_db.save_transcript(document)
        return

    def update_prompt_with_clean_transcript(self, video_object_id, video_id):
        document = self.transcript_db.find_transcript_by_video_reference_id(video_object_id)
        logger.info("Transcript found for: " + str(video_object_id))
        document_prompt = self.transcript_db.prompt_context_raw_collection.find_one({"video_id": video_id})

        self.transform_transcript_timestamp(document, document_prompt)

        self.transcript_db.insert_prompt_context_index(document_prompt, video_id)

    def transform_transcript_timestamp(self, document, document_prompt):
        transcript = document['cleaned_transcript']

        pattern = r"\[(\d+:\d+:\d+\.\d+)\]\s*([^[]+)"
        matches = re.findall(pattern, transcript)
        transcript_data = [{"time": timestamp_to_seconds(time), "text": text.strip()} for time, text in matches]

        pending_text = []
        index = 0
        for section in document_prompt["result"]["sections"]:
            split_text = re.split(r"\[Transcript]", section["content"])
            start_time = timestamp_to_seconds(section["start"])
            end_time = timestamp_to_seconds(section["end"])
            while index < len(transcript_data):
                if start_time <= transcript_data[index]['time'] <= end_time:
                    pending_text.append(
                        "(" + seconds_to_timestamp(transcript_data[index]['time']) + ") " + transcript_data[index][
                            "text"])
                    index += 1
                else:
                    break
            section["content"] = split_text[0] + "[Transcript] " + "\n".join(pending_text)
            pending_text = []
        return document_prompt

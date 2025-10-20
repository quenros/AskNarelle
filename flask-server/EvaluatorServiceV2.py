import asyncio
import json
import os
from typing import List

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings

from ragas import SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    FactualCorrectness, LLMContextPrecisionWithReference, ResponseRelevancy, Faithfulness, LLMContextRecall
)

from chatservice.chatservice import ChatService

load_dotenv()
class EvaluatorService:
    def __init__(self, chat_service: ChatService, questions=None, ground_truths=None):
        self.chat_service = chat_service

        self.llm_evaluator = AzureChatOpenAI(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("OPENAI_API_VERSION"),
            azure_deployment=os.environ.get("YOUR_DEPLOYMENT_NAME_4O"),
            temperature=0
        )

        self.metrics = [
            faithfulness,
            answer_relevancy,
            FactualCorrectness(),
        ]
        self.questions = [
            "When is the first lab test?",
            "Are lab sessions compulsory?",
            "What courses is SC1007 a pre-requisite to?",
            "What are some algorithm design strategies?",
            "Are the tutorial sessions online or physical?",
            "What is the title of this course?",
            "What are the assessment components?",
            "Who is the lecturer of this course?",
            "What is the course schedule for this course?",
            "What is the purpose of tutorials?",
            "What will be covered in the next lecture?",
            "Are there any recommended books for this course?",
            "What is the definition of an algorithm?",
            "Who will be teaching the second half of this course?",
            "What is the learning outcome of this course?"
        ]
        self.ground_truths = [
            "3rd March",
            "Lab sessions are highly encouraged, but not compulsory.",
            "SC1007 is a pre-requisite to SC2101 Algorithm Design and Analysis, SC3000 Artificial Intelligence, SC2207 Introduction to Databases, and SC3020 Database System Principles.",
            "Some algorithm design strategies include Brute Force and Exhaustive Search, Divide-and-Conquer, Greedy Strategy, Decrease-and-Conquer, Transform-and-Conquer, and Iterative Improvement.",
            "The tutorial sessions will be conducted online.",
            "The title of the course is SC1007 Data Structures and Algorithms.",
            "There are three assessment components. They are Assignments (40%), Two Lab Tests (20% each), Final Quiz (20%).",
            "The lecturer of this course is Dr. Loke Yuan Ren.",
            "The course schedule for this course is: Week 1 - Introduction to Data Structure and Algorithm; Week 2 - Linked List (LL) - Linear Search; Week 3 - Analysis of Algorithm, Tutorial T1, Lab L1 – LL; Week 4 - Stack and Queue (SQ) - Arithmetic Expression, AS1: LL; Week 5 - Tree Traversal – Binary Search, Tutorial T2, Lab L2 – SQ, AS2: SQ; Week 6 - AVL, Huffman Coding, Lab L3 – Tree 1, AS3: Tree; Week 7 - Revision, Tutorial T3, Lab L4 – Tree 2, AS4: Tree 2; Recess Week - Lab Test 1 (3 March 2022); Week 8 - Hash Table + Graph Representation; Week 9 - BFS, DFS, Lab L5 – Graph; Week 10 - Backtracking, Permutation, Tutorial T4, Lab L6 – BFS, DFS, AS5; Week 11 - Dynamic Programming, Tutorial T5, Lab L7 – Backtracking, AS6; Week 12 - Bipartite Graph – Matching Problem, Tutorial T6, Lab L8 – DP, AS7; Week 13 - Revision, AS8; Week 14 - Lab2 Test + Quiz",
            "The purpose of tutorials is to focus on understanding the concepts, facilitate discussions and clarify doubt.",
            "The next lecture will cover the definition of pointers and structures, static data structure and dynamic data structure, computer memory layouts, memory allocation, memory deallocation, examples and common mistakes. If there is additional time, concepts of linked lists will be covered.",
            "The lecturer recommended the book Introduction to Algorithms and Introduction to The Design & Analysis of Algorithms.",
            "From Introduction to The Design & Analysis of Algorithms, an algorithm is a sequence of unambiguous instructions for solving a problem, i.e., for obtaining a required output for any legitimate input in a finite amount of time. From Introduction to Algorithms, an algorithm is any well-defined computational procedure that takes some value, or set of values, as input and produces some value, or set of values, as output.",
            "The second half of this course will be taught by Dr. Luu Anh Tuan.",
            "After SC1007 Data Structures and Algorithms, students must be able to select appropriate data structures, implement algorithms to solve real world problems using C programming, and conduct complexity analysis of algorithms."
        ]

        self.time_sensitive_questions = [
            "What is mentioned at 19 minutes mark?",
            "When did the lecturer mention about the course overview?",
            "When did the lecturer talked about how SC1007 relates to other courses?",
            "What is mentioned at the end of the lecture?",
            "What time will the lecture start?"
        ]

        self.time_sensitive_answers = [
            "The lecturer mentions about the course schedule, with more emphasis on details of the lab tests. He also mentions about the learning outcomes.",
            "The course overview is mentioned at 28:00 to 31:00.",
            "The lecturer talked about it when mentioning CS Curriculum Structure. This is mentioned from 23:40 to 25:00.",
            "The lecturer answered queries from students. These queries are mainly course-related information.",
            "It will start at around 12:30pm."
        ]


    async def get_dataset(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_clean(video_id, self.questions[i])
            print(str(i) + " get_dataset " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.questions[i], self.ground_truths[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.questions[i], answer, self.ground_truths[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.questions[i],
                'ground_truth': self.ground_truths[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_pre(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt(video_id, self.questions[i])
            print(str(i) + " get_dataset_pre " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.questions[i], self.ground_truths[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.questions[i], answer, self.ground_truths[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.questions[i],
                'ground_truth': self.ground_truths[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_pre.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_naive(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_naive(video_id, self.questions[i])
            print(str(i) + " get_dataset_naive " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.questions[i], self.ground_truths[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.questions[i], answer, self.ground_truths[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.questions[i],
                'ground_truth': self.ground_truths[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_naive.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_clean_naive(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_clean_naive(video_id, self.questions[i])
            print(str(i) + " get_dataset_naive " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.questions[i], self.ground_truths[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.questions[i], answer, self.ground_truths[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.questions[i],
                'ground_truth': self.ground_truths[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_naive_clean.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_t(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.time_sensitive_questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_clean(video_id, self.time_sensitive_questions[i])
            print(str(i) + " get_dataset " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.time_sensitive_questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.time_sensitive_questions[i], self.time_sensitive_answers[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.time_sensitive_questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.time_sensitive_questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.time_sensitive_questions[i], answer, self.time_sensitive_answers[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.time_sensitive_questions[i],
                'ground_truth': self.time_sensitive_answers[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_t.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_pre_t(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.time_sensitive_questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt(video_id, self.time_sensitive_questions[i])
            print(str(i) + " get_dataset_pre " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.time_sensitive_questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.time_sensitive_questions[i], self.time_sensitive_answers[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.time_sensitive_questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.time_sensitive_questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.time_sensitive_questions[i], answer, self.time_sensitive_answers[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.time_sensitive_questions[i],
                'ground_truth': self.time_sensitive_answers[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_pre_t.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_naive_t(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.time_sensitive_questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_naive(video_id, self.time_sensitive_questions[i])
            print(str(i) + " get_dataset_naive " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.time_sensitive_questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.time_sensitive_questions[i], self.time_sensitive_answers[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.time_sensitive_questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.time_sensitive_questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.time_sensitive_questions[i], answer, self.time_sensitive_answers[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.time_sensitive_questions[i],
                'ground_truth': self.time_sensitive_answers[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_naive_t.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def get_dataset_clean_naive_t(self, video_id):
        results = []  # This will store the results for all questions

        # Iterate through the questions and evaluate the answers
        for i in range(len(self.time_sensitive_questions)):
            retrieval_results, context = self.chat_service.retrieve_results_prompt_clean_naive(video_id, self.time_sensitive_questions[i])
            print(str(i) + " get_dataset_naive " + str(context))
            answer = self.chat_service.generate_video_prompt_response(retrieval_results, self.time_sensitive_questions[i])

            # Evaluate metrics
            context_precision = await self.evaluate_context_precision(self.time_sensitive_questions[i], self.time_sensitive_answers[i], context)
            response_relevancy = await self.evaluate_response_relevancy(self.time_sensitive_questions[i], answer, context)
            faithfulness_result = await self.evaluate_faithfulness(self.time_sensitive_questions[i], answer, context)
            context_recall = await self.evaluate_context_recall(self.time_sensitive_questions[i], answer, self.time_sensitive_answers[i],
                                                                context)

            # Store the results for this question in a dictionary
            result = {
                'question': self.time_sensitive_questions[i],
                'ground_truth': self.time_sensitive_answers[i],
                'context': context,
                'answer': answer,
                'context_precision': context_precision,
                'response_relevancy': response_relevancy,
                'faithfulness_result': faithfulness_result,
                'context_recall': context_recall
            }

            results.append(result)

        with open("evaluation_results_naive_clean_t.json", mode='w', newline='') as jsonfile:
            json.dump(results, jsonfile, indent=4)

    async def evaluate_context_precision(self, user_input: str, reference: str, retrieved_contexts: List[str]):
        context_precision = LLMContextPrecisionWithReference(llm=LangchainLLMWrapper(self.llm_evaluator))
        sample = SingleTurnSample(
            user_input=user_input,
            reference=reference,
            retrieved_contexts=retrieved_contexts,
        )
        result = await context_precision.single_turn_ascore(sample)
        return result

    async def evaluate_response_relevancy(self, user_input: str, response: str, retrieved_contexts: List[str]):
        sample = SingleTurnSample(
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts
        )

        evaluator_embeddings = AzureOpenAIEmbeddings(
            openai_api_version="2023-05-15",
            azure_deployment="text-embedding-ada-002",
            model="text-embedding-ada-002",
        )

        scorer = ResponseRelevancy(llm=LangchainLLMWrapper(self.llm_evaluator), embeddings=LangchainEmbeddingsWrapper(evaluator_embeddings))
        result = await scorer.single_turn_ascore(sample)
        print(result)
        return result

    async def evaluate_faithfulness(self, user_input: str, response: str, retrieved_contexts: List[str]):
        sample = SingleTurnSample(
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts
        )

        scorer = Faithfulness(llm=LangchainLLMWrapper(self.llm_evaluator))

        result = await scorer.single_turn_ascore(sample)
        print(result)
        return result

    async def evaluate_context_recall(self, user_input: str, response: str, reference:str, retrieved_contexts: List[str]):
        sample = SingleTurnSample(
            user_input=user_input,
            response=response,
            reference=reference,
            retrieved_contexts=retrieved_contexts
        )

        scorer = LLMContextRecall(llm=LangchainLLMWrapper(self.llm_evaluator))

        result = await scorer.single_turn_ascore(sample)
        print(result)
        return result

async def main():
    service = ChatService()

    # evaluator_service = EvaluatorService(chat_service=service)
    # await evaluator_service.get_dataset(video_id="ygec01914d")
    # await evaluator_service.get_dataset_pre(video_id="ygec01914d")
    # await evaluator_service.get_dataset_naive(video_id="ygec01914d")
    # await evaluator_service.get_dataset_clean_naive(video_id="ygec01914d")

    evaluator_service = EvaluatorService(chat_service=service)
    await evaluator_service.get_dataset_t(video_id="ygec01914d")
    await evaluator_service.get_dataset_pre_t(video_id="ygec01914d")
    await evaluator_service.get_dataset_naive_t(video_id="ygec01914d")
    await evaluator_service.get_dataset_clean_naive_t(video_id="ygec01914d")



# Run the main function
if __name__ == '__main__':
    asyncio.run(main())

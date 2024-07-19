# Copyright 2024 Google, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from zoneinfo import ZoneInfo
from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.api_core.client_options import ClientOptions
from google.cloud import storage
from google.cloud.storage.blob import Blob
from util.llm import modelg
from util.settings import PROJECT, LOCATION, engine_ds_name
from vertexai.generative_models import GenerationConfig, Tool
from vertexai.preview.generative_models import grounding
import ntpath
import re


project = PROJECT
location = LOCATION
datastore_project_id = project
data_store_id = engine_ds_name
serving_config_id = "default_search"
storage_client = storage.Client()

#                                                                                EU requires specific API endpoint
client_options = (ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com") if location != 'global' else None)

summary_spec = discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
        # Use top 5 results for summary
        summary_result_count=5,
        include_citations=True,
        ignore_adversarial_query=True,
#        model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(preamble=preamble)
        )

# Specific to summarization Search
summary_search_client = discoveryengine.SearchServiceClient(client_options=client_options)
summary_serving_config = summary_search_client.serving_config_path(project=datastore_project_id,
                                                                   location=location,
                                                                   data_store=data_store_id,
                                                                   serving_config=serving_config_id)

content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(max_snippet_count=1, return_snippet=True),
    summary_spec=summary_spec,
    extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
#        max_extractive_answer_count=1,   # turns on extractive content
#        max_extractive_segment_count=5,  # extractive segments
    )
)

def list_parser(text: str):
    text = text.replace(" - ", "\n- ")
    text = re.sub(r' ([0-9]+\. )', r'\n\1', text, 100)
    return text

def get_doc_url(uri):
    """Transform the uri of the document into an url that can be accessed via browser

    Args:
        uri (str): uri of the document

    Returns:
        Browser accessible url of the document
    """
    blob = Blob.from_string(uri, storage_client)
    url = blob.public_url
    return url.replace('googleapis', 'mtls.cloud.google')

def search_engine_summary(query):
    """Executes the summary search algorithm by calling Vertex AI Search with summarization. Returns a summary of the result plus a list of documents, snippets, extracts and segments.
    
    Args:
        query (str): Query from user

    Returns:
        dict: {'response': (str) Answer text, 'documents': (list[dict]) List of documents}
    """
    request = discoveryengine.SearchRequest(
        serving_config=summary_serving_config,
        query=query,
        page_size=10,
        filter='',
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        )
    )
    search_response = summary_search_client.search(request)
    response = {'response': list_parser(search_response.summary.summary_text), 'documents': []}
    for i, result in enumerate(search_response.results, 1):
        struct_data = result.document.derived_struct_data
        doc = {'name': f'[{i}] ' + ntpath.basename(struct_data['link']), 'url': get_doc_url(struct_data['link']), 'snippets': [], 'extracts': [], 'segments': []}
        for snippet in struct_data.get('snippets', []):
            doc['snippets'].append(snippet['snippet'])
        for extract in struct_data.get('extractive_answers', []):
            doc['extracts'].append({'pageNumber': extract.get('pageNumber'), 'extract': extract.get('content')})
        for extract in struct_data.get('extractive_segments', []):
            doc['segments'].append({'pageNumber': extract.get('pageNumber'), 'extract': extract.get('content'), 'relevanceScore': extract.get('relevanceScore')})
        response['documents'].append(doc)
    return response

def search_engine_grounding(history, query):
    """Executes the grounding search algorithm by calling an LLM with grounding enabled. Returns a summary of the result plus a list of documents. This algorithm does not return any snippets, extracts or segments.
    
    Args:
        query (str): Query from user

    Returns:
        dict: {'response': (str) Answer text, 'documents': (list[dict]) List of documents}
    """

    current_time = datetime.now(tz=ZoneInfo("Europe/Berlin"))
    llm_prompt = f"Today is {current_time.strftime('%A, %B %-d %Y')}. The current time is {current_time.strftime('%-H:%M')}.\n"\
                "You are a cheerful chat companion. Your input are a chat history between a chatbot and a user. "\
                "You are given the latest question from the user which you have to answer in a safe and joyful way.\n"\
                "Provide answers that are suitable for any audience. Try to keep your responses to a few lines of text. For long answers, only mention the highlights.\n\n"\
                f"Chat history:\n{history}\n"\
                f"user: {query}\n"\
                "chatbot: "
    tool = Tool.from_retrieval(grounding.Retrieval(grounding.VertexAISearch(datastore=f'projects/{project}/locations/{location}/collections/default_collection/dataStores/{engine_ds_name}')))
    llm_response = modelg.generate_content(llm_prompt, tools=[tool], generation_config=GenerationConfig(temperature=0.0))
    for candidate in llm_response.candidates:
        docs = [{'name': f'[{i}] ' + c.retrieved_context.title, 'url': get_doc_url(c.retrieved_context.uri), 'snippets': [], 'extracts': [], 'segments': []} for i,c in enumerate(candidate.grounding_metadata.grounding_chunks, start=1)]
        break
    return {'response': llm_response.text, 'documents': docs}

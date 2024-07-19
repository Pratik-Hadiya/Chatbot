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

import os
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import aiplatform
from google.api_core.client_options import ClientOptions
import json
from google.cloud import storage
from google.api_core.exceptions import AlreadyExists, Conflict
from util.settings import PROJECT, REGION, LOCATION, engine_ds_name


DOCDIR = os.getenv("DOCDIR")
if not DOCDIR:
    print('DOCDIR environment variable not set')
    exit(1)
region = REGION
project = PROJECT
location = LOCATION

aiplatform.init(project=project)
client_options = ( ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com") if location != 'global' else None )

# First, create datastore
ds_client = discoveryengine.DataStoreServiceClient(client_options=client_options)
ds_parent = ds_client.collection_path(project=project, location=location, collection='default_collection')
ds_path = ds_client.data_store_path(project=project, location=location, data_store=engine_ds_name)
print(f"Creating datastore {ds_path}...")
datastore = discoveryengine.DataStore(name=ds_path, display_name='Datastore for DB Hackathon',
                                         industry_vertical=discoveryengine.IndustryVertical.GENERIC,
                                         solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
                                         content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED)
ds_request = discoveryengine.CreateDataStoreRequest(parent=ds_parent, data_store=datastore, data_store_id=engine_ds_name)
try:
    operation = ds_client.create_data_store(request=ds_request)
    the_datastore = operation.result()
    print(f"Datastore {ds_path} created successfully")
except AlreadyExists:
    print(f'Datastore {engine_ds_name} already exists - no action')

# Now import documents into datastore
our_bucket_name = 'dbhackathon_input_' + project
json_bucket_name = our_bucket_name
if DOCDIR.startswith('gs://'):
    # We have a bucket for our documents
    input_bucket_name = DOCDIR[5:]
else:
    # We have a directory for our documents
    input_bucket_name = our_bucket_name
metadata_name = 'metadata.jsonl'
print()
# Create our bucket if not exists
print("Creating our bucket...")
storage_client = storage.Client()
bucket_client = storage.Client(project=project)
try:
    bucket_client.create_bucket(our_bucket_name, location=region)
    print(f"Created bucket {our_bucket_name}")
except Conflict:
    print(f"Our bucket {our_bucket_name} already exists - no action")

# Create Metadata for import
metadata = []
# {"id":"doc-3","structData":{"title":"test_doc_3"},"content":{"mimeType":"application/pdf","uri":"gs://test-bucket-12345678/test_doc_4.pdf"}}
input_bucket = storage_client.bucket(input_bucket_name)
if input_bucket_name == our_bucket_name: # if the input is a directory
    enumerator = enumerate(os.listdir(DOCDIR))
else:
    enumerator = enumerate([n.name for n in input_bucket.list_blobs(fields='items(name)')])
for i, f in enumerator:
    fname = f
    metadata.append({'id': str(i),
                    'structData': {'file': fname},
                    'content': {'mimeType': 'application/pdf', 'uri': 'gs://' + input_bucket_name + '/' + fname}})
metajson = '\n'.join([json.dumps(m) for m in metadata])
json_bucket = storage_client.bucket(json_bucket_name)
print('Uploading metadata')
blob = json_bucket.blob(metadata_name)
blob.upload_from_string(metajson)

# Upload files to input bucket if necessary
if input_bucket_name == our_bucket_name: # if the input is a directory
    for meta in metadata:
        fname = meta['structData']['file']
        print(f'Uploading {fname}')
        blob = input_bucket.blob(fname)
        blob.upload_from_filename(DOCDIR + '/' + fname)

print()
# Clean datastore of any previous contents
print('Purging documents in data store', engine_ds_name)
document_client = discoveryengine.DocumentServiceClient(client_options=client_options)
document_parent = document_client.branch_path(project=project, location=location, data_store=engine_ds_name, branch='default_branch')
purgeRequest = discoveryengine.PurgeDocumentsRequest(parent=document_parent, filter='*', force=True)
try:
    d_operation = document_client.purge_documents(request=purgeRequest)
    d_response = d_operation.result()
    print(f'Purged {d_response.purge_count} documents')
except Exception as e:
    print(f'ERROR trying to purge: {e}')

print()
# Now for the import
print('Starting importing documents into data store.', engine_ds_name)
jsonfile = 'gs://' + json_bucket_name + '/' + metadata_name
import_error_bucket = os.environ.get('IMPORT_ERROR_BUCKET', 'gs://' + our_bucket_name + '/errors')
import_request = discoveryengine.ImportDocumentsRequest(
    parent=document_parent,
    gcs_source=discoveryengine.GcsSource(input_uris=[jsonfile], data_schema='document'),
    error_config=discoveryengine.ImportErrorConfig(gcs_prefix=import_error_bucket),
    reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL)
try:
    ds_operation = document_client.import_documents(request=import_request)
except Exception as e:
    print(f'ERROR trying to import: {e}')

print()
# Then create engine
engine_client = discoveryengine.EngineServiceClient(client_options=client_options)
engine_path = engine_client.engine_path(project=project, location=location, collection='default_collection', engine=engine_ds_name)
print(f"Creating engine {engine_path}...")
engine_client = discoveryengine.EngineServiceClient(client_options=client_options)
engine_config = discoveryengine.Engine.SearchEngineConfig(search_tier=discoveryengine.SearchTier.SEARCH_TIER_ENTERPRISE, search_add_ons=[discoveryengine.SearchAddOn.SEARCH_ADD_ON_LLM])
engine = discoveryengine.Engine(name=engine_path, display_name="Search Engine for DB Hackathon", data_store_ids=[engine_ds_name], solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH, search_engine_config=engine_config)
engine_parent = engine_client.collection_path(project=project, location=location, collection='default_collection')
engine_request = discoveryengine.CreateEngineRequest(parent=engine_parent, engine=engine, engine_id=engine_ds_name)
try:
    e_operation = engine_client.create_engine(request=engine_request)
    the_engine = e_operation.result()
    print(f"Engine {engine_path} created successfully")
except AlreadyExists:
    print(f'Engine {engine_ds_name} already exists - no action')

print()
print("Waiting for document import to complete. This can take a while...")
print("May time out after 900s which does not mean a failed import")
ds_response = ds_operation.result()
print(f'Imported documents with {len(ds_response.error_samples)} errors')

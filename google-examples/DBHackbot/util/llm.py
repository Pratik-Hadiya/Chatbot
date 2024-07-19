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


from vertexai.preview.generative_models import GenerativeModel
from google.cloud import aiplatform
from util.settings import PROJECT, REGION

# The purpose of this module is to initialize Vertex AI and
# load all LLMs in a central place, only once.
# These operations take time and memory and doing this in a
# central module saves both.

aiplatform.init(project=PROJECT, location=REGION)
modelg = GenerativeModel("gemini-1.5-flash-001")

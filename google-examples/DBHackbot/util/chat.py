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

import streamlit as st

user_avatar = 'assets/user.png'
assistant_avatar = 'assets/assistant.png'
icons = {"chatbot": assistant_avatar,
         'user': user_avatar}

# Each chat message is a dict
# { 'text': str, 'content': <any other data type that st.write accepts> }

def prepare_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

def write_chat(message):
    if message.get("text"):
        st.markdown(message["text"])
    if "content" in message:
        st.write(message["content"])

def display_chat_message(message):
    with st.chat_message(message["role"], avatar=icons[message["role"]]):
        write_chat(message)

def display_chat():
    for message in st.session_state.messages:
        display_chat_message(message)

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
import time
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from util.chat import prepare_chat, display_chat, display_chat_message, icons
from util.references import prepare_references, display_references
from util.docsnsnips import cleanup_json
from util.llm import modelg
from util.rag import search_engine_grounding
from util.auth import check_password
from vertexai.preview.generative_models import GenerationConfig, Part

# This is a streamlit application. Streamlit has a particular model of how operate:
# The entire code is run through each time an action occurs on the page.
# Refer to https://docs.streamlit.io/get-started/fundamentals/main-concepts

# Sticky title at top - this is an unofficial trick
header = st.container()
header.title("Gemini assistant")
header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)
### Custom CSS for the sticky header
st.markdown(
    """
<style>
    div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
        position: sticky;
        top: 2.875rem;
        background-color: white;
        z-index: 999;
        gap: 0rem;
    }
    .fixed-header {
        border-bottom: 1px solid black;
    }

    h1 {
        font-size: calc(0.7rem + 0.9vw);
    }
</style>
    """,
    unsafe_allow_html=True
)

# First check basic auth
if not check_password():
    st.stop()  # Do not continue if check_password is not True.

# Initialize chat history
prepare_chat()

# Initialize references
prepare_references()

# Display references on app rerun
references = display_references()

# Prefab questions
question_keys = ["q1", "q2", "q3"]
questions = ["How fast is an elephant?", "Tell me a Chuck Norris joke", "What is the business model of alphabet?"]
def prefab_question():
    for i, key in enumerate(question_keys):
        if key in st.session_state and st.session_state[key] is True:
            st.session_state.ask_this = questions[i]
            break

# Uncomment the next line if you want to disable prefabs
# st.session_state.been_here_before = True

# Display prefab questions
# only until first question has been asked
if 'been_here_before' not in st.session_state:
    col1, col2, col3 = st.columns(3)
    col1.button(f"**Option 1**\n\n\n\n*{questions[0]}*", key=question_keys[0], on_click=prefab_question)
    col2.button(f"**Option 2**\n\n\n\n*{questions[1]}*", key=question_keys[1], on_click=prefab_question)
    col3.button(f"**Option 3**\n\n\n\n*{questions[2]}*", key=question_keys[2], on_click=prefab_question)
    # Custom button styling
    st.markdown(
        """
    <style>
        button[data-testid="baseButton-secondary"] {
            background-color: gray;
            border-color: gray;
            color: white;
            height: 100px;
            width: 100%;
            align-items: unset;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
    st.session_state.been_here_before = True

# Put all chat messages in one space
chat_space = st.container()

# Display chat messages from history on app rerun
with chat_space:
    display_chat()

def ask_gemini(history, query, image=None, temperature=1):
    current_time = datetime.now(tz=ZoneInfo("Europe/Berlin"))
    llm_prompt1 = f"Today is {current_time.strftime('%A, %B %-d %Y')}. The current time is {current_time.strftime('%-H:%M')}.\n"\
                "You are a cheerful chat companion. Your input are a chat history between a chatbot and a user. "\
                "You are given the latest question from the user which you have to answer in a safe and joyful way.\n"\
                "Provide answers that are suitable for any audience. Try to keep your responses to a few lines of text. For long answers, only mention the highlights.\n\n"\
                f"Chat history:\n{history}\n"
    llm_prompt2 = f"user: {query}\n"\
                "chatbot: "
    contents = [Part.from_text(llm_prompt1)]
    if image:
        contents.append(Part.from_image(image))
    contents.append(Part.from_text(llm_prompt2))
    generation_config = GenerationConfig(candidate_count=1, max_output_tokens=2048, temperature=temperature)
    response = {'response': ''}
    try:
        gen_response = modelg.generate_content(contents, stream=False, generation_config=generation_config)
    except Exception as e:
        response['response'] = f'Oh no! A problem occurred:\n{str(e)}\n'
    response['response'] += gen_response.text
    return response

def make_history():
    history = ''
    for message in st.session_state.messages[:-1]:
        history += f'{message["role"]}: {message["text"]}\n'
    return history    

def get_intent(history, query):
    llm_prompt = f"""Given a conversation history between a user and a chatbot, your job is to identify the intent of the latest query by the user.
The intent can either be related to the company alphabet, including its subsidiaries (also called bets), or the intent can be other.
Provide your output as JSON. Do not generate any other content. This is what your output should look like:
{{
   "intent": "alphabet" if the question is related to alphabet or its subsidiaries; "other" if it is any other topic
}}

Conversation history:
{history}

Latest query:
{query}

Your result:
""" 
    contents = [Part.from_text(llm_prompt)]
    generation_config = GenerationConfig(candidate_count=1, max_output_tokens=400)
    try:
        gen_response = modelg.generate_content(contents, stream=False, generation_config=generation_config)
    except Exception as e:
        print(f'Exception during detect intent: {e}')
        return {'intent': 'other'}
    intent = cleanup_json(str(gen_response.text))
    try:
        intent = json.loads(intent)
    except Exception as e:
        print(f"ERROR - llm response parsing failed for '{gen_response.text}': {e}")
        intent = {'intent': 'other'}
    return intent

# -----------------------------------------------
#  This is where the actual chat logic resides
# -----------------------------------------------
def handle_query(query):
    # We can do lots of stuff here: Find out user intent, generate SQL, generate pictures,
    # search for information...
    history = make_history()
    intent = get_intent(history, query)
    print(intent)
    if intent['intent'] == 'alphabet':
        #response = {'response': "It's RAG time!"}
        response = search_engine_grounding(history, query)
    else:
        # We can also just ask Gemini
        response = ask_gemini(history, query)
    return response

def ask_question(prompt):
    global references
    # Add user message to chat history
    newmsg = {"role": "user", "text": prompt}
    st.session_state.messages.append(newmsg)
    # Display user message in chat message container
    with chat_space:
        display_chat_message(newmsg)
    # Ask the AI to handle our request
    response = handle_query(prompt)
    # Display assistant response in chat message container
    with chat_space:
        with st.chat_message("chatbot", avatar=icons["chatbot"]):
            full_response = ""
            # Simulate stream of response with milliseconds delay
            assistant_response = response.get('response')
            if assistant_response and assistant_response != '':
                response_placeholder = st.empty()
                for chunk in assistant_response.split():
                    full_response += chunk + " "
                    time.sleep(0.02)
                    # Add a blinking cursor to simulate typing
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(assistant_response)
    # Add assistant response to chat history
    newmsg = {"role": "chatbot", "text": assistant_response }
    st.session_state.messages.append(newmsg)
    # Handle references if there are any
    st.session_state.references = []
    ref_flag = False
    for doc in response.get('documents',[]):
        newref = dict(doc)
        st.session_state.references.append(newref)
        ref_flag = True
    # references = display_references(references)
    # instead we rerun because of a bug in streamlit: empties are not cleared properly leading to clutter in sidebar
    if ref_flag:
        st.rerun()

# Do we have a prefab question?
if st.session_state.get("ask_this"):
    hlp = st.session_state.ask_this
    st.session_state.ask_this = None
    ask_question(hlp)

# Accept user input
if prompt := st.chat_input("What would you like to know?"):
    ask_question(prompt)
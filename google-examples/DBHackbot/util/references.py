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
# references are shown in the left sidebar
# they get accumulated over time

def prepare_references():
    if 'references' not in st.session_state:
        st.session_state.references = []

def write_reference(ref):
    if 'name' in ref:
        hlp = ref['name'].split()
        while hlp[1][0].isnumeric():
            hlp[1] = hlp[1][1:]
        st.markdown(f"[{' '.join(hlp)}]({ref['url']})")
    if 'page' in ref:
        st.markdown(f"**[Page {ref['page']}]**")
    if len(ref.get('snippets', [])) > 0:
        st.markdown(f"*{ref['snippets'][0]}*", unsafe_allow_html=True)

# display references in the sidebar
def display_references(references = None):
    global refcounter
    if not references:
        references = st.sidebar.empty()
    references.empty()
    with references.container():
        for ref in st.session_state.references:
            write_reference(ref)
    return references
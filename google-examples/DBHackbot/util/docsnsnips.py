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


def following_char(i: int, s: str) -> str:
    '''
    Find next character that is not whitespace.
    '''
    i += 1
    while i < len(s) and s[i].isspace():
        i += 1
    if i < len(s):
        return s[i]
    else:
        return ''


def cleanup_json(x: str):
    """Takes a string with supposed JSON content and eliminates excess characters at beginning and end.
    
    Args:
        x (str): String containing a JSON structure. May contain leading and trailing characters outside of JSON.
 
    Returns:
        str: Retuns the substring representig the JSON structure. Returns None if JSON could not be found.
    """
    startBrace = x.find('{')
    if startBrace == -1:
        return None
    endBrace = x.rfind('}')
    if endBrace == -1:
        return None
    if startBrace > endBrace:
        return None
    the_json = x[startBrace:endBrace+1].replace('\n', ' ')
    # Now check for unescaped '"' characters
    inquote = False
    i = 0 
    while i < len(the_json):
        if the_json[i] == '"' and (i == 0 or the_json[i-1] != '\\'):
            if inquote:
                if following_char(i, the_json).isalpha():
                    # Looks like quoting inside a string
                    # We must escape this quote and the next
                    the_json = the_json[0:i] + '\\' + the_json[i:]
                    i += 2
                    while the_json[i] != '"' and i < len(the_json):
                        i += 1
                    if i < len(the_json):
                        the_json = the_json[0:i] + '\\' + the_json[i:]
                        i += 2
                else:
                    inquote = False
                    i += 1
            else:
                inquote = True
                i += 1
        else:
            i += 1
    return the_json


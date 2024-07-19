#!/bin/bash

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

FGRED="\033[0;31m"
FGGREEN="\033[0;32m"
FGCYAN="\033[0;36m"
FGBLUE="\033[0;34m"
FGNORMAL="\033[0m"

function blue {
    echo -e "$FGBLUE$1$FGNORMAL"
}

function green {
    echo -e "$FGGREEN$1$FGNORMAL"
}

function red {
    echo -e "$FGRED$1$FGNORMAL"
}

if ! [ -f set_it_up.sh ]; then
    red "Script must be run from directory where it resides!"
    return
fi

# Enable required APIs
blue "Checking enabled APIs..."
SERVICES="iam.googleapis.com aiplatform.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com discoveryengine.googleapis.com run.googleapis.com serviceusage.googleapis.com storage.googleapis.com"
ENABLED="`gcloud services list`"
for service in $SERVICES ; do
    if [[ "$ENABLED" == *"$service"* ]]; then
        green "$service is enabled"
    else
        red "$service should be enabled!"
    fi
done

if [ -d .venv ]; then
    blue "Virtual Python environment already exists"
else
    blue "Creating virtual Python environment"
    python3 -m venv .venv
fi

green "Activating virtual Python environment"
. .venv/bin/activate

# Install Python packages
blue "Installing python dependencies"
pip install -q pip --upgrade
pip install -q -r requirements.txt

# Get value for DOCDIR
# Could be bucket or directory
if [[ -z "${DOCDIR}" ]]; then
    red "Document directory environment variable is not set"
    while [[ -z "${NEWDIR}" ]]
    do
        read -p "Enter a directory name (sampledoc) or bucket uri (gs://... without trailing '/'): " NEWDIR
    done
else
    green "Current value of DOCDIR is $DOCDIR"
    read -p "Enter new value (directory name or bucket uri without trailing '/') or press ENTER to leave as is: " NEWDIR
fi

if [[ -n "${NEWDIR}" ]]; then
    export DOCDIR=$NEWDIR
    blue "DOCDIR set to $DOCDIR"
fi

# Create Search App with Datastore
# This has to be done from Python because gcloud doesn't offer it
blue "Creating Vertex AI Search App"
python create_searchapp.py

echo ""
green "Setup script completed."
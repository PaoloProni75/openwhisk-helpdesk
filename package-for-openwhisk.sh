#!/bin/bash

echo "Packaging OpenWhisk Helpdesk actions..."

# Create clean directory structure
rm -rf build/
mkdir -p build/

# Package Orchestrator (main service)
echo "Packaging orchestrator..."
zip -r build/helpdesk-orchestrator.zip \
    __main__.py \
    config/ \
    libs/ \
    -x "**/__pycache__/*" "**/.pytest_cache/*" "**/test_*" "**/*.pyc"

# Package Similarity service
echo "Packaging similarity..."
cd similarity/
cat > __main__.py << 'EOF'
import sys
import os
sys.path.append(os.path.dirname(__file__))
from main import main
EOF

zip -r ../build/helpdesk-similarity.zip \
    __main__.py \
    *.py \
    ../config/ \
    ../libs/ \
    ../requirements.txt \
    -x "__pycache__/*" "*.pyc"

rm __main__.py
cd ..

# Package Ollama service
echo "Packaging ollama..."
cd ollama/
cat > __main__.py << 'EOF'
import sys
import os
sys.path.append(os.path.dirname(__file__))
from main import main
EOF

zip -r ../build/helpdesk-ollama.zip \
    __main__.py \
    *.py \
    ../config/ \
    ../libs/ \
    ../requirements.txt \
    -x "__pycache__/*" "*.pyc"

rm __main__.py
cd ..

echo "Packaging complete! Files created in build/ directory:"
ls -la build/

export remoteServer=15.161.146.166
export SRC=/Users/paoloproni/Documents/UniBZ/Tesi/openwhisk-helpdesk
export KEYS=/Users/paoloproni/OllamaServerKeys.pem

scp -i $KEYS $SRC/build/helpdesk-similarity.zip ubuntu@$remoteServer://home/ubuntu
scp -i $KEYS $SRC/build/helpdesk-orchestrator.zip ubuntu@$remoteServer://home/ubuntu
scp -i $KEYS $SRC/build/helpdesk-ollama.zip ubuntu@$remoteServer://home/ubuntu  

echo ""
echo "Deploy commands:"
echo "wsk package create helpdesk"
echo "wsk action create helpdesk/orchestrator build/helpdesk-orchestrator.zip --kind python:3.11 --timeout 120000 --memory 1024"
echo "wsk action create helpdesk/similarity build/helpdesk-similarity.zip --kind python:3.11 --timeout 60000 --memory 512"
echo "wsk action create helpdesk/ollama build/helpdesk-ollama.zip --kind python:3.11 --timeout 120000 --memory 512"

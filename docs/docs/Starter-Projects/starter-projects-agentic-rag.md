---
title: Agentic RAG
slug: /starter-projects-agentic-rag
---

# Agentic RAG Implementation in AutoAgent

Agentic RAG (Retrieval-Augmented Generation) is an intelligent retrieval system that can decide whether and how to retrieve information from a knowledge base as needed. Traditional RAG methods (such as [chunkRAG](https://github.com/chonkie-ai/chonkie), [MiniRAG](https://github.com/HKUDS/MiniRAG), [LightRAG](https://github.com/HKUDS/LightRAG), and [GraphRAG](https://github.com/microsoft/graphrag)) have limitations as they rely on predefined workflows and struggle to determine if they have acquired sufficient knowledge to answer questions. To make the RAG process more intelligent, we introduce Agentic RAG powered by [AutoAgent](https://github.com/HKUDS/AutoAgent), implementing intelligent storage, retrieval, and response.

## System Architecture

### 1. Required Imports
```python
from constant import DOCKER_WORKPLACE_NAME
from autoagent.environment.docker_container import init_container
from autoagent.io_utils import read_yaml_file, get_md5_hash_bytext
from autoagent.agents import get_rag_agent
from autoagent.core import AutoAgent
from autoagent.environment.docker_env import DockerEnv, DockerConfig, with_env
import argparse
import asyncio
import csv
from tqdm import trange
import os
import json
import time
```

### 2. Environment Configuration
```python
def get_env(container_name: str = 'gaia_test', 
            model: str = 'gpt-4o-mini-2024-07-18',
            git_clone: bool = False, 
            setup_package: str = 'lite_pkgs'):
    workplace_name = DOCKER_WORKPLACE_NAME
    docker_config = DockerConfig(
        container_name=container_name,
        workplace_name=workplace_name,
        communication_port=12345,
        conda_path='/home/user/micromamba'
    )
    docker_env = DockerEnv(docker_config)
    return docker_env
```

The system runs in a Docker container, providing an isolated environment with the following main configurations:
- Container name
- Working directory
- Communication port
- Conda environment path

### 3. RAG Agent Setup
```python
async def main(container_name: str = 'gaia_test', model: str = 'gpt-4o-mini-2024-07-18', git_clone: bool = False, setup_package: str = 'lite_pkgs', test_pull_name: str = 'test_pull_1010', debug: bool = True, task_instructions: str = None):
    workplace_name = DOCKER_WORKPLACE_NAME
    # Docker environment is optional
    # docker_env = get_env(container_name, model, git_clone, setup_package, test_pull_name, debug)
    # docker_env.init_container()

    task_instructions = "YOUR TASK"

    rag_agent = get_rag_agent(model)#, rag_env=docker_env)
    mc = AutoAgent()
```

The system uses the AutoAgent framework to manage RAG agents, with key features including:
- Asynchronous operation support
- Configurable language models
- Flexible message handling mechanism

### 4. Query Processing Flow
```python
context_variables = {
    "working_dir": DOCKER_WORKPLACE_NAME,
    "user_query": task_instructions
}
messages = [{"role": "user", "content": task_instructions}]
response = await mc.run_async(
    agent=codeact_agent, 
    messages=messages,
    max_turns=10, 
    context_variables=context_variables, 
    debug=debug
)
```

Query processing includes the following steps:
1. Setting context variables
2. Building message format
3. Asynchronous agent execution
4. Controlling maximum conversation turns
5. Debug mode support

## Usage

We put a basic usage example in [`AutoAgent/evaluation/multihoprag`](https://github.com/HKUDS/AutoAgent/tree/main/evaluation/multihoprag).


### 1. Basic Usage
```bash
current_dir=$(dirname "$(readlink -f "$0")")

cd $current_dir
cd ../
export DOCKER_WORKPLACE_NAME=workplace_rag
export EVAL_MODE=True
export DEBUG=True
export BASE_IMAGES=tjbtech1/gaia-bookworm:v2
export COMPLETION_MODEL=claude-3-5-sonnet-20241022

python run_rag.py --model gpt-4o-mini-2024-07-18 --container_name gaia_test
```

### 2. Parameter Description
- `--container_name`: Docker container name
- `--model`: Language model to use
- `--git_clone`: Whether to clone code
- `--setup_package`: Package type to install
- `--debug`: Whether to enable debug mode

## Key Features

1. **Asynchronous Processing**: Using `asyncio` for improved processing efficiency
2. **Containerized Deployment**: Using Docker for environment consistency
3. **Flexible Configuration**: Support for various models and parameter configurations
4. **Batch Processing**: Support for batch query processing
5. **Result Tracking**: Saving queries and responses for evaluation and analysis

## Important Notes

1. Ensure proper Docker environment configuration
2. Check model access permissions and configurations
3. Set appropriate maximum conversation turns
4. Maintain data format consistency
5. Regular backup of result files
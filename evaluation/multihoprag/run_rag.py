from constant import DOCKER_WORKPLACE_NAME
from metachain.environment.docker_container import init_container
from metachain.io_utils import read_yaml_file, get_md5_hash_bytext
from metachain.agents import get_rag_agent
from metachain.core import MetaChain
from metachain.environment.docker_env import DockerEnv, DockerConfig, with_env
import argparse
import asyncio
import csv
from tqdm import trange
import os
import json
import time
def get_args(): 
    parser = argparse.ArgumentParser(description="working@tjb-tech")
    parser.add_argument('--container_name', type=str, default='gaia_test')
    parser.add_argument('--model', type=str, default='gpt-4o-mini-2024-07-18')
    parser.add_argument('--git_clone', action='store_true', default=False)
    parser.add_argument('--setup_package', type=str, default='lite_pkgs')
    parser.add_argument('--debug', action='store_true', default=False)
    args = parser.parse_args()
    return args

def get_env(container_name: str = 'gaia_test', model: str = 'gpt-4o-mini-2024-07-18', git_clone: bool = False, setup_package: str = 'lite_pkgs', test_pull_name: str = 'test_pull_1010', debug: bool = True):
    workplace_name = DOCKER_WORKPLACE_NAME
    docker_config = DockerConfig(container_name=container_name, workplace_name=workplace_name, communication_port=12345, conda_path='/home/user/micromamba')
    docker_env = DockerEnv(docker_config)
    return docker_env



def append_to_json(file_path, entry):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
    else:
        data = []

    data.append(entry)

    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)



async def main(container_name: str = 'gaia_test', model: str = 'gpt-4o-mini-2024-07-18', git_clone: bool = False, setup_package: str = 'lite_pkgs', test_pull_name: str = 'test_pull_1010', debug: bool = True, task_instructions: str = None):
    workplace_name = DOCKER_WORKPLACE_NAME
    # docker_env = get_env(container_name, model, git_clone, setup_package, test_pull_name, debug)
    # docker_env.init_container()

    csv_file_path = './MultiHopRAG.csv'
    json_path = './result.json'

    question_list=[]
    GA_LIST=[]
    with open(csv_file_path, mode='r', encoding='utf-8') as question_file:
        reader = csv.DictReader(question_file)
        for row in reader:
            question_list.append(row['query'])
            GA_LIST.append(row['answer'])
    
    row_count = 0

    with open(json_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        row_count = len(data)

      
    for QUESTIONid in trange(row_count,len(question_list)):#

        task_instructions = question_list[QUESTIONid]
        #answer: row[1]

        codeact_agent = get_rag_agent(model)#, rag_env=docker_env)
        mc = MetaChain()
        # try:
        context_variables = {"working_dir": DOCKER_WORKPLACE_NAME,"user_query": task_instructions}
        messages = [{"role": "user", "content": task_instructions}]
        response = await mc.run_async(agent=codeact_agent, messages=messages,max_turns=10, context_variables=context_variables, debug=debug)


        data_new = {
            "query": task_instructions,
            "gold_answer": GA_LIST[QUESTIONid],
            "answer": response.messages[-1]['content']
        }

        append_to_json(json_path, data_new)
        

if __name__ == "__main__":
    args = get_args()
    asyncio.run(main(args.container_name, args.model, args.git_clone, args.setup_package, args.test_pull_name, args.debug))

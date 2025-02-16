import argparse
from constant import DOCKER_WORKPLACE_NAME
from datasets import load_dataset
import huggingface_hub
from autoagent import MetaChain
from autoagent.logger import MetaChainLogger, LoggerManager
from evaluation.utils import make_metadata, prepare_dataset, update_progress, check_port_available, run_evaluation, clean_msg
from evaluation.types import EvalMetadata, EvalOutput
import autoagent.agents as agenthub
import os.path as osp
import pandas as pd
import asyncio
import re
import os
import shutil
from autoagent.registry import registry
from evaluation.gaia.scorer import question_scorer
import json
# from autoagent.util import run_command_in_container
from autoagent.environment.docker_env import DockerEnv, DockerConfig, check_container_ports, check_container_exist, check_container_running
from autoagent.environment.browser_env import BrowserEnv
from autoagent.environment.markdown_browser import RequestsMarkdownBrowser
from autoagent.types import Response
from autoagent.util import function_to_json
from autoagent.main import run_in_client, run_in_client_non_async
from autoagent.agents.meta_agent.tool_editor import get_tool_editor_agent
from autoagent.environment.utils import setup_metachain
import subprocess
DATASET_CACHE_DIR = osp.join(osp.dirname(__file__), 'data')
# Note: You should run this script in the root directory of the project autoagent
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--container_name', type=str, default='gaia_test')
    parser.add_argument('--model', type=str, default='claude-3-5-sonnet-20241022')
    parser.add_argument('--git_clone', action='store_true', default=False)
    parser.add_argument('--setup_package', type=str, default=None)
    parser.add_argument('--test_pull_name', type=str, default='main')
    parser.add_argument('--debug', action='store_true', default=False)
    # metadata
    parser.add_argument('--agent_func', type=str, default='get_system_triage_agent')
    parser.add_argument('--eval_note', type=str, default=None)
    parser.add_argument('--eval_output_dir', type=str, default='./evaluation_results')
    parser.add_argument('--data_split', type=str, default=None)
    # gaia level
    parser.add_argument('--level', type=str, default='1')
    parser.add_argument('--eval_n_limit', type=int, default=None)
    parser.add_argument('--port', type=int, default=12345)
    parser.add_argument('--eval_num_workers', type=int, default=1)
    args = parser.parse_args()
    return args

def get_config(metadata: EvalMetadata, instance_id: str):
    container_name = metadata.container_name+f'_{instance_id}'
    
    port_info = check_container_ports(container_name)
    port = metadata.port
    if port_info:
        port = port_info[0]
    else:
        # while not check_port_available(port):
        #     port += 1
        # 使用文件锁来确保端口分配的原子性
        import filelock
        lock_file = os.path.join(os.getcwd(), ".port_lock")
        lock = filelock.FileLock(lock_file)
        
        with lock:
            port = metadata.port
            while not check_port_available(port):
                port += 1
                print(f'{port} is not available, trying {port+1}')
            # 立即标记该端口为已使用
            with open(os.path.join(os.getcwd(), f".port_{port}"), 'w') as f:
                f.write(container_name)
    local_root = os.path.join(os.getcwd(), f"workspace_gaia_whole", f"gaia_eval_{instance_id}")
    os.makedirs(local_root, exist_ok=True)
    docker_config = DockerConfig(
        workplace_name=DOCKER_WORKPLACE_NAME,
        container_name=container_name,
        communication_port=port,
        conda_path='/root/miniconda3',
        local_root=local_root,
        git_clone=metadata.git_clone,
        test_pull_name=metadata.test_pull_name,
    )
    return docker_config

def process_instance(
    instance: pd.Series,
    metadata: EvalMetadata,
    logger: MetaChainLogger,
) -> EvalOutput:
    docker_config = get_config(metadata, instance_id=instance['instance_id'])
    code_env = None
    try:
        

        code_env, web_env, file_env = create_environment(docker_config)
        local_workplace = code_env.local_workplace
        docker_workplace = code_env.docker_workplace
        

        # Setup the logger properly, so you can run multi-processing to parallelize the evaluation
        logger.info(f'Starting evaluation for instance {instance["instance_id"]}.')

        if instance['file_name'] != '':
            assert metadata.data_split is not None
            src_file = os.path.join(
                DATASET_CACHE_DIR, '2023', metadata.data_split, instance['file_name']
            )
            assert os.path.exists(src_file)
            extension_name = instance['file_name'].split('.')[-1]
            dest_file = os.path.join(local_workplace, f'file.{extension_name}')
            shutil.copy(src_file, dest_file)
            file_name = dest_file.split('/')[-1]
        else:
            dest_file = None
        

        # Prepare instruction
        instruction = f"{instance['Question']}\n"
        logger.info(f'Instruction: {instruction}')
        if dest_file:
            instruction += f"\n\nThe mentioned file is provided in the workspace at: {osp.join(docker_workplace, file_name)}"

        instruction += 'IMPORTANT: Any agent cannot stop using tools until the task is done. Don\'t tell me how to do bot do it using tools!\n'
        instruction += 'IMPORTANT: System Triage Agent must hand off the task to the suitable agents, and finally answer the question util there is no more sub-task to do.\n'
        instruction += 'IMPORTANT: When you meet something you are not sure about, you should use the `Web Surfer Agent` to search the web. And when you are required to compute something, you should use the `Programming Agent` to compute. Take Advantage of agents as much as possible.\n'
        instruction += 'IMPORTANT: You should ONLY interact with the environment provided to you AND NEVER ASK FOR HUMAN HELP.\n'
        instruction += 'Please encapsulate your final answer (answer ONLY) within <solution> and </solution>.\n'
        instruction += (
            'For example: The answer to the question is <solution> 42 </solution>.\n'
        )
        
        logger.info(f'Instruction:\n{instruction}')

        system_triage_agent = registry.agents[metadata.agent_func](model=metadata.model)
        messages = [
            {
                'role': 'user',
                'content': instruction
            }
        ]

        context_variables = {"code_env": code_env, "web_env": web_env, "file_env": file_env}
        # Here's how you can run the agent (similar to the `main` function) and get the final task state
        tool_editor_agent = get_tool_editor_agent(model=metadata.model)
        response: Response | None = asyncio.run(
            run_in_client(
                agent=system_triage_agent,
                messages=messages,
                context_variables = context_variables, 
                logger=logger, 
                meta_agent=tool_editor_agent,
                docker_config=docker_config, 
                code_env=code_env,
            )
        )
        # response: Response | None = run_in_client_non_async(
        #     agent=system_triage_agent,
        #     messages=messages,
        #     context_variables = context_variables, 
        #     logger=logger
        # )
        messages.extend(response.messages)
        # save messages to a file
        messages_file = osp.join(metadata.eval_output_dir, f"gaia_{instance['instance_id']}", f'messages_{metadata.agent_func.replace("get_", "")}.json')
        os.makedirs(osp.dirname(messages_file), exist_ok=True)
        messages = clean_msg(messages)
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=4)
        # ======= Attempt to evaluate the agent's edits =======
        # If you are working on simpler benchmark that only evaluates the final model output (e.g., in a MessageAction)
        # You can simply get the LAST `MessageAction` from the returned `state.history` and parse it for evaluation.

        if response is None:
            raise ValueError('Response should not be None.')

        model_answer_raw = response.messages[-1]['content']

        # attempt to parse model_answer
        model_answer = re.findall(r'<solution>(.*?)</solution>', model_answer_raw)
        if len(model_answer) == 0:
            logger.info(f'Failed to parse model answer: {model_answer_raw}', title='WARNING', color='yellow')
            model_answer = model_answer_raw
        else:
            model_answer = model_answer[0]

        logger.info(
            f'Final message: {model_answer} | Ground truth: {instance["Final answer"]}',
            title='INFO', color='green'
        )
        score = question_scorer(
            model_answer=model_answer, ground_truth=instance['Final answer']
        )
        test_result = {
            'score': score,
            'model_answer_raw': model_answer_raw,
            'model_answer': model_answer,
            'ground_truth': instance['Final answer'],
        }


        # Save the output
        output = EvalOutput(
            instance_id=instance['instance_id'],
            instance=instance.to_dict(),
            instruction=instance['Question'],
            metadata=metadata,
            messages=messages,
            test_result=test_result,
        )
    finally:
        # 清理资源
        if code_env is not None:
            try:
                # 停止容器
                code_env.stop_container()
                logger.info(f"Container {docker_config.container_name} stopped successfully")        
                # 可选：删除容器
                # subprocess.run(["docker", "rm", docker_config.container_name], 
                #              capture_output=True, text=True)
                # logger.info(f"Container {docker_config.container_name} removed successfully")
                
                # 可选：删除工作目录
                    
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
                
        # 清理端口标记文件
        port_file = os.path.join(os.getcwd(), f".port_{docker_config.communication_port}")
        if os.path.exists(port_file):
            os.remove(port_file)
            logger.info(f"Port {docker_config.communication_port} released")
    return output

def map_instance_to_port(dataset: pd.DataFrame, metadata: EvalMetadata):
    port_dict = {}
    for idx, row in dataset.iterrows():
        port_dict[row['instance_id']] = metadata.port + idx
        

def create_environment(docker_config: DockerConfig):
    """
    1. create the code environment
    2. create the web environment
    3. create the file environment
    """
    code_env = DockerEnv(docker_config)
    code_env.init_container()
    
    web_env = BrowserEnv(browsergym_eval_env = None, local_root=docker_config.local_root, workplace_name=docker_config.workplace_name)
    file_env = RequestsMarkdownBrowser(viewport_size=1024 * 5, local_root=docker_config.local_root, workplace_name=docker_config.workplace_name, downloads_folder=os.path.join(docker_config.local_root, docker_config.workplace_name, "downloads"))
    
    return code_env, web_env, file_env
def main(args):
    metadata: EvalMetadata = make_metadata(
        model=args.model,
        dataset_name="gaia",
        agent_func=args.agent_func,
        eval_note=args.eval_note,
        eval_output_dir=args.eval_output_dir,
        data_split=args.data_split,
        details={'gaia-level': args.level},
        port=args.port,
        container_name=args.container_name,
        git_clone=args.git_clone,
        test_pull_name=args.test_pull_name,
    )
    log_path = osp.join(metadata.eval_output_dir, 'logs', f'agent_{metadata.model}.log')
    LoggerManager.set_logger(MetaChainLogger(log_path))

    dataset = load_dataset('gaia-benchmark/GAIA', args.level)
    huggingface_hub.snapshot_download(
        'gaia-benchmark/GAIA',
        repo_type='dataset',
        local_dir=DATASET_CACHE_DIR,
    )
    gaia_tests = dataset[metadata.data_split].to_pandas()
    gaia_tests.rename(columns={'task_id': 'instance_id'}, inplace=True)
    
    output_file = osp.join(metadata.eval_output_dir, 'output.jsonl')
    prepared_dataset = prepare_dataset(gaia_tests, output_file, args.eval_n_limit)

    run_evaluation(
        dataset=prepared_dataset,
        metadata=metadata,
        output_file=output_file,
        num_workers=args.eval_num_workers,
        process_instance_func=process_instance,
    )



if __name__ == "__main__":
    args = get_args()
    main(args)
    # print(check_container_exist('gaia_lite_eval_c61d22de-5f6c-4958-a7f6-5e9707bd3466'))
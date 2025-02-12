import click
import importlib
from autoagent import MetaChain
from autoagent.util import debug_print
import asyncio
@click.group()
def cli():
    """The command line interface for autoagent"""
    pass

@cli.command()
@click.option('--model', default='gpt-4o-2024-08-06', help='the name of the model')
@click.option('--agent_func', default='get_dummy_agent', help='the function to get the agent')
@click.option('--query', default='...', help='the user query to the agent')
@click.argument('context_variables', nargs=-1)
def agent(model: str, agent_func: str, query: str, context_variables):
    """
    Run an agent with a given model, agent function, query, and context variables.
    Args:
        model (str): The name of the model.
        agent_func (str): The function to get the agent.
        query (str): The user query to the agent.
        context_variables (list): The context variables to pass to the agent.
    Usage:
        mc agent --model=gpt-4o-2024-08-06 --agent_func=get_weather_agent --query="What is the weather in Tokyo?" city=Tokyo unit=C timestamp=2024-01-01
    """ 
    context_storage = {}
    for arg in context_variables:
        if '=' in arg:
            key, value = arg.split('=', 1)
            context_storage[key] = value
    agent_module = importlib.import_module(f'autoagent.agents')
    try:
        agent_func = getattr(agent_module, agent_func)
    except AttributeError:
        raise ValueError(f'Agent function {agent_func} not found, you shoud check in the `autoagent.agents` directory for the correct function name')
    agent = agent_func(model)
    mc = MetaChain()
    messages = [
        {"role": "user", "content": query}
    ]
    response = mc.run(agent, messages, context_storage, debug=True)
    debug_print(True, response.messages[-1]['content'], title = f'Result of running {agent.name} agent', color = 'pink3')
    return response.messages[-1]['content']

@cli.command()
@click.option('--workflow_name', default=None, help='the name of the workflow')
@click.option('--system_input', default='...', help='the user query to the agent')
def workflow(workflow_name: str, system_input: str):
    """命令行函数的同步包装器"""
    return asyncio.run(async_workflow(workflow_name, system_input))

async def async_workflow(workflow_name: str, system_input: str):
    """异步实现的workflow函数"""
    workflow_module = importlib.import_module(f'autoagent.workflows')
    try:
        workflow_func = getattr(workflow_module, workflow_name)
    except AttributeError:
        raise ValueError(f'Workflow function {workflow_name} not found...')
    
    result = await workflow_func(system_input)  # 使用 await 等待异步函数完成
    debug_print(True, result, title=f'Result of running {workflow_name} workflow', color='pink3')
    return result
from autoagent.registry import register_agent
from autoagent.tools.meta.edit_agents import list_agents, create_agent, delete_agent, run_agent
from autoagent.tools.terminal_tools import execute_command
from autoagent.types import Agent
from autoagent.io_utils import read_file

@register_agent(name = "Agent Editor Agent", func_name="get_agent_editor_agent")
def get_agent_editor_agent(model: str) -> str:
    """
    The agent editor is an agent that can be used to edit the agents.
    """
    def instructions(context_variables):
        return f"""\
You are an agent editor agent that can be used to edit the agents. You are working on a Agent framework named MetaChain, and your responsibility is to edit the agents in the MetaChain, so that the agents can be used to help the user with their request.

The existing agents are shown below:
{list_agents(context_variables)}

If you want to create a new agent, you should: 
1. follow the format of the `get_dummy_agent` below: 
```python
{read_file('autoagent/agents/dummy_agent.py')}
```
2. you successfully create the agent only after you have successfully run the agent with the `run_agent` function to satisfy the user's request.

3. If you encounter any error while creating and running the agent, like dependency missing, you should use the `execute_command` function to install the dependency.

[IMPORTANT] The `register_plugin_agent` registry function is strictly required for a agent implementation to be recognized by the MetaChain framework.
"""
    tool_list = [list_agents, create_agent, delete_agent, run_agent, execute_command]
    return Agent(
        name="Agent Editor Agent", 
        model=model, 
        instructions=instructions,
        functions=tool_list,
        tool_choice = "required", 
        parallel_tool_calls = False
    )

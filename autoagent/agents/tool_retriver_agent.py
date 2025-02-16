from autoagent.types import Agent
from autoagent.tools import (
    get_api_plugin_tools_doc
)
from autoagent.util import make_message, make_tool_message
from autoagent.registry import register_agent
@register_agent(name = "Tool Retriver Agent", func_name="get_tool_retriver_agent")
def get_tool_retriver_agent(model: str):
    def instructions(context_variables):
        return \
f"""
You are a tool retriver agent.
You are given a task instruction, and you need to retrieve the tool docs for the task using function `get_tool_doc`.
Note that if you want to complete the task, you may need to use more than one tool, so you should retrieve the tool docs for all the tools you may need. Finally, you should give a merged tool doc consisting of all the tool docs you retrieved, and the implementation code of each tool should be included in the tool doc.
"""
    return Agent(
    name="Tool Retriver Agent",
    model=model,
    instructions=instructions,
    functions=[get_api_plugin_tools_doc],
    )
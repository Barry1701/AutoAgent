from .filesurfer_agent import get_filesurfer_agent
from .programming_agent import get_coding_agent
from .websurfer_agent import get_websurfer_agent
from autoagent.registry import register_agent
from autoagent.types import Agent, Result
from autoagent.tools.inner import case_resolved, case_not_resolved

@register_agent(name = "System Triage Agent", func_name="get_system_triage_agent")
def get_system_triage_agent(model: str, **kwargs):
    """
    This is the `System Triage Agent`, it can help the user to determine which agent is best suited to handle the user's request under the current context, and transfer the conversation to that agent.
    
    Args:
        model: The model to use for the agent.
        **kwargs: Additional keyword arguments, `file_env`, `web_env` and `code_env` are required.
    """
    filesurfer_agent = get_filesurfer_agent(model)
    websurfer_agent = get_websurfer_agent(model)
    coding_agent = get_coding_agent(model)
    instructions = \
f"""You are a helpful assistant that can help the user with their request.
Based on the state of solving user's task, your responsibility is to determine which agent is best suited to handle the user's request under the current context, and transfer the conversation to that agent. And you should not stop to try to solve the user's request by transferring to another agent only until the task is completed.

There are three agents you can transfer to:
1. use `transfer_to_filesurfer_agent` to transfer to {filesurfer_agent.name}, it can help you to open any type of local files and browse the content of them.
2. use `transfer_to_websurfer_agent` to transfer to {websurfer_agent.name}, it can help you to open any website and browse any content on it.
3. use `transfer_to_coding_agent` to transfer to {coding_agent.name}, it can help you to write code to solve the user's request, especially some complex tasks.
"""
    tool_choice = "required" 
    tools = [case_resolved, case_not_resolved] if tool_choice == "required" else []
    system_triage_agent = Agent(
        name="System Triage Agent",
        model=model, 
        instructions=instructions,
        functions=tools,
        tool_choice = tool_choice, 
        parallel_tool_calls = False,
    )
    def transfer_to_filesurfer_agent(sub_task_description: str):
        """
        Args:
            sub_task_description: The detailed description of the sub-task that the `System Triage Agent` will ask the `File Surfer Agent` to do.
        """
        return Result(value=sub_task_description, agent=filesurfer_agent)
    def transfer_to_websurfer_agent(sub_task_description: str):
        return Result(value=sub_task_description, agent=websurfer_agent)
    def transfer_to_coding_agent(sub_task_description: str):
        return Result(value=sub_task_description, agent=coding_agent)
    def transfer_back_to_triage_agent(task_status: str):
        """
        Args:
            task_status: The detailed description of the task status after a sub-agent has finished its sub-task. A sub-agent can use this tool to transfer the conversation back to the `System Triage Agent` only when it has finished its sub-task.
        """
        return Result(value=task_status, agent=system_triage_agent)
    system_triage_agent.agent_teams = {
        filesurfer_agent.name: transfer_to_filesurfer_agent,
        websurfer_agent.name: transfer_to_websurfer_agent,
        coding_agent.name: transfer_to_coding_agent
    }
    system_triage_agent.functions.extend([transfer_to_filesurfer_agent, transfer_to_websurfer_agent, transfer_to_coding_agent])
    filesurfer_agent.functions.append(transfer_back_to_triage_agent)
    websurfer_agent.functions.append(transfer_back_to_triage_agent)
    coding_agent.functions.append(transfer_back_to_triage_agent)
    return system_triage_agent

    
from autoagent.types import Agent
from autoagent.tools import tool_dummy
from typing import Union
from autoagent.registry import register_plugin_agent # import the register_agent function from the registry

@register_plugin_agent(name = "Dummy Agent", func_name="get_dummy_agent") # You must register the agent in the registry, otherwise the agent will not be loaded. The name of register_agent is get_xxx_agent.
def get_dummy_agent(model: str):
    """
    This is a dummy agent, it's used for demonstrating the usage of the autoagent.
    Args:
        model: The model to be used for the agent.
    Returns:
        An agent instance.
    """
    def dummy_instructions(context_variables: dict):
        """
        The function should take the context_variables as an argument, and return a string. The context_variables is a dictionary, and it's track the important variables of the agent in the whole conversation.
        The instructions should be concise and clear, and it's very important for the agent to follow the instructions.
        """
        tmp_variables = context_variables.get("tmp_variables", {})
        return f"""...""" 
    return Agent(
        name="Dummy Agent", # The name of the agent, you can change it in different scenes.
        model=model, # The default model is gpt-4o-2024-08-06, you can change it to other models if user specified.
        instructions="..." or dummy_instructions, # the instructions of the agent, the instructions can be a string or a function that returns a string. If it is a function, the function should take the context_variables as an argument, and return a string. The instructions should be concise and clear, and it's very important for the agent to follow the instructions.
        functions=[tool_dummy], # The tools of the agent, you can add different tools in different scenes.
    )

"""
Form to create an agent: 

agent_name = "Dummy Agent"
agent_description = "This is a dummy agent, it's used for demonstrating the usage of the autoagent."
agent_instructions = "..." | "...{global_variables}..."
agent_tools = [tool_dummy]
"""
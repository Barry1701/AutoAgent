from autoagent.types import Agent
from autoagent.tools import (
    push_changes, submit_pull_request
)
from autoagent.registry import register_agent


@register_agent(name = "Github Agent", func_name="get_github_agent")
def get_github_agent(model: str):
    def instructions(context_variables):
        return \
f"""You are an agent that helps user to manage the GitHub repository named 'autoagent'. 
The user will give you the suggestion of the changes to be pushed to the repository.
Follow the following routine with the user:
1. First, use `push_changes` to push the changes to the repository. (If the user want to push all the changes, use `push_changes` with `file_paths=None` as the argument.)
2. Then, ask the user whether to submit a pull request to a target branch. (If yes, give the `target_branch`)
3. If the user wants to submit a pull request, use `submit_pull_request` to submit the pull request, if not, just ignore this step.
"""
    return Agent(
    name="Github Agent",
    model=model,
    instructions=instructions,
    functions=[push_changes, submit_pull_request],
    parallel_tool_calls = False
    )

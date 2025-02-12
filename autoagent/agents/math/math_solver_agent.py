from autoagent.types import Agent

from autoagent.registry import register_plugin_agent

@register_plugin_agent(name="Math Solver Agent", func_name="get_math_solver_agent")
def get_math_solver_agent(model: str):
    '''
    This agent solves mathematical problems using analytical and systematic approaches.
    '''
    instructions = 'You are responsible for solving mathematical problems using a systematic approach. You should:\n1. Use the provided conditions and objective to formulate a solution strategy\n2. Break down complex problems into smaller steps\n3. Apply appropriate mathematical concepts and formulas\n4. Show clear step-by-step work and explanations\n5. Verify the solution matches the problem requirements'
    return Agent(
    name="Math Solver Agent",
    model=model,
    instructions=instructions,
    functions=[]
    )


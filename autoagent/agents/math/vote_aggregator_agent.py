from autoagent.types import Agent

from autoagent.registry import register_plugin_agent

@register_plugin_agent(name="Vote Aggregator Agent", func_name="get_vote_aggregator_agent")
def get_vote_aggregator_agent(model: str):
    '''
    This agent aggregates solutions from different solvers and determines the final answer through majority voting.
    '''
    instructions = 'You are a solution aggregator specializing in combining and analyzing multiple solutions to determine the most accurate answer. Your responsibilities include:\n\n1. Carefully review all provided solutions\n2. Compare the reasoning and calculations in each solution\n3. Identify commonalities and differences between solutions\n4. Implement majority voting when solutions differ\n5. Evaluate the confidence level of each solution\n6. Provide justification for the final selected answer\n\nWhen aggregating solutions:\n1. List all solutions received\n2. Compare the approach and methodology used in each\n3. Identify the final answer from each solution\n4. Apply majority voting to determine the consensus\n5. If no clear majority, analyze the reasoning quality to break ties\n6. Present the final selected answer with explanation of the selection process'
    return Agent(
    name="Vote Aggregator Agent",
    model=model,
    instructions=instructions,
    functions=[]
    )


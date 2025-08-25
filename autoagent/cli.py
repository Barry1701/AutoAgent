import click
from typing import Dict, Any

# --- Import explicit agents here (no need to export via __init__.py) ---
from autoagent.agents.staff_directory_agent import staff_directory_agent
from autoagent.agents.camera_agent import camera_agent
from autoagent.agents.doors_agent import doors_agent
from autoagent.agents.operations_agent import operations_agent


AGENTS = {
    "staff_directory_agent": staff_directory_agent,
    "camera_agent": camera_agent,
    "doors_agent": doors_agent,
    "operations_agent": operations_agent,
}


@click.group()
def cli():
    """The command line interface for AutoAgent"""
    pass


@cli.command(name="agent")
@click.option('--model', default='gpt-5', help='LLM model name to pass in context')
@click.option(
    '--agent_func',
    required=True,
    type=click.Choice(sorted(AGENTS.keys())),
    help='Agent function to run'
)
@click.option('--query', required=True, help='User query passed to the agent function')
@click.argument('context_variables', nargs=-1)
def run_agent(model: str, agent_func: str, query: str, context_variables):
    """
    Run a single agent function.
    Extra context variables can be passed as key=value after the options.
    """
    # Parse extra key=value into a dict
    context: Dict[str, Any] = {'model': model}
    for arg in context_variables:
        if '=' in arg:
            k, v = arg.split('=', 1)
            context[k] = v

    fn = AGENTS.get(agent_func)
    if fn is None:
        raise click.ClickException(
            f"Unknown agent '{agent_func}'. Available: {', '.join(AGENTS.keys())}"
        )

    click.echo(f"\n🤖 [Agent]: {agent_func}\n📨 [Query]: {query}\n")
    try:
        # Prefer new signature: fn(query, context=...)
        result = fn(query, context=context)
    except TypeError:
        # Fallback for legacy signature: fn(query)
        result = fn(query)

    click.echo("✅ Response:")
    click.echo(result)


if __name__ == "__main__":
    cli()

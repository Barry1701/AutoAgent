import click
import importlib
from typing import Dict, Any


@click.group()
def cli():
    """The command line interface for AutoAgent"""
    pass


@cli.command(name="agent")
@click.option('--model', default='gpt-5', help='LLM model name to pass in context')
@click.option('--agent_func', required=True,
              help='Function name exported from autoagent.agents (e.g., staff_directory_agent)')
@click.option('--query', required=True, help='User query passed to the agent function')
@click.argument('context_variables', nargs=-1)
def run_agent(model: str, agent_func: str, query: str, context_variables):
    """
    Run a single agent function exposed by autoagent.agents.<agent_func>(query, context).
    Context variables can be passed as extra arguments in the form key=value.
    """
    # Parse extra key=value into a dict
    context: Dict[str, Any] = {'model': model}
    for arg in context_variables:
        if '=' in arg:
            k, v = arg.split('=', 1)
            context[k] = v

    # Dynamically import agent function from autoagent.agents
    try:
        agents_module = importlib.import_module('autoagent.agents')
    except Exception as e:
        raise click.ClickException(f"Failed to import 'autoagent.agents': {e}")

    try:
        fn = getattr(agents_module, agent_func)
    except AttributeError:
        raise click.ClickException(
            f"Agent function '{agent_func}' not found in autoagent.agents.\n"
            f"Make sure it's imported/exported in autoagent/agents/__init__.py"
        )

    click.echo(f"\n🤖 [Agent]: {agent_func}\n📨 [Query]: {query}\n")
    try:
        result = fn(query, context=context)
    except TypeError:
        # Fallback for legacy signature: fn(query) without context
        result = fn(query)

    click.echo("✅ Response:")
    click.echo(result)


if __name__ == "__main__":
    cli()

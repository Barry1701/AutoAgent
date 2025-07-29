import click
import importlib
from autoagent import MetaChain
from autoagent.util import debug_print
import asyncio
from constant import DOCKER_WORKPLACE_NAME
from autoagent.io_utils import read_yaml_file, get_md5_hash_bytext, read_file
from autoagent.environment.utils import setup_metachain
from autoagent.types_custom import Response
from autoagent import MetaChain
from autoagent.util import ask_text, single_select_menu, print_markdown, debug_print, UserCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
import argparse
from datetime import datetime
from autoagent.agents.meta_agent import tool_editor, agent_editor
from autoagent.tools.meta.edit_tools import list_tools
from autoagent.tools.meta.edit_agents import list_agents
from loop_utils.font_page import MC_LOGO, version_table, NOTES, GOODBYE_LOGO
from rich.live import Live
from autoagent.environment.docker_env import DockerEnv, DockerConfig, check_container_ports
from autoagent.environment.local_env import LocalEnv
from autoagent.environment.browser_env import BrowserEnv
from autoagent.environment.markdown_browser import RequestsMarkdownBrowser
from evaluation.utils import update_progress, check_port_available, run_evaluation, clean_msg
import os
import os.path as osp
from autoagent.agents import get_system_triage_agent
from autoagent.logger import LoggerManager, MetaChainLogger 
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.panel import Panel
import re
from autoagent.cli_utils.metachain_meta_agent import meta_agent
from autoagent.cli_utils.metachain_meta_workflow import meta_workflow
from autoagent.cli_utils.file_select import select_and_copy_files
from evaluation.utils import update_progress, check_port_available, run_evaluation, clean_msg
from constant import COMPLETION_MODEL
from autoagent.agents.staff_directory_agent import staff_directory_agent

import click
from autoagent.agents.staff_directory_agent import staff_directory_agent

@click.group()
def cli():
    """The command line interface for AutoAgent"""
    pass

@cli.command()
@click.option('--model', default='gpt-4', help='The name of the model')
@click.option('--agent_func', default='staff_directory_agent', help='The function to get the agent')
@click.option('--query', default='', help='The user query to the agent')
@click.argument('context_variables', nargs=-1)
def main(model, agent_func, query, context_variables):
    """
    Run an agent with a given model, agent function, query, and context variables.
    """
    # Map string to function (only one for now, expand later)
    if agent_func == 'staff_directory_agent':
        agent = staff_directory_agent
    else:
        raise ValueError(f"Unknown agent function: {agent_func}")

    print(f"\n🤖 [Agent]: {agent_func}")
    print(f"📨 [Query]: {query}\n")
    
    # Uruchom agenta
    result = agent(query)
    print("✅ Response:")
    print(result)

if __name__ == "__main__":
    cli()

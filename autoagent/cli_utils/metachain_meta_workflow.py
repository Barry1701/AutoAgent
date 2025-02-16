from autoagent import MetaChain
from autoagent.util import ask_text, single_select_menu, print_markdown, debug_print, UserCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from autoagent.logger import LoggerManager, MetaChainLogger 
from rich.console import Console
from rich.panel import Panel
from autoagent.agents.meta_agent.workflow_former import get_workflow_former_agent
from autoagent.agents.meta_agent.workflow_creator import get_workflow_creator_agent
import re
from autoagent.agents.meta_agent.worklow_form_complie import parse_workflow_form, WorkflowForm

def workflow_profiling(workflow_former, client, messages, context_variables, requirements, debug):
    messages.append({"role": "user", "content": requirements + """
Directly output the form in the XML format without ANY other text.
"""})
    response = client.run(workflow_former, messages, context_variables, debug=debug)
    output_xml_form = response.messages[-1]["content"]
    messages.extend(response.messages)

    MAX_RETRY = 3
    for i in range(MAX_RETRY):
        workflow_form = parse_workflow_form(output_xml_form)
        if isinstance(workflow_form, WorkflowForm):
            break
        elif isinstance(workflow_form, str):
            print(f"Error parsing XML to workflow form: {workflow_form}. Retry {i+1}/{MAX_RETRY}")
            messages.append({"role": "user", "content": f"Error parsing XML to workflow form, the error message is: {workflow_form}\nNote that there are some special restrictions for creating workflow form, please try again."})
            response = client.run(workflow_former, messages, context_variables, debug=debug)
            output_xml_form = response.messages[-1]["content"]
            messages.extend(response.messages)
        else:
            raise ValueError(f"Unexpected error: {workflow_form}")
    return workflow_form, output_xml_form, messages

def workflow_editing(workflow_creator_agent, client, messages, context_variables, workflow_form, output_xml_form, requirements, task, debug, suggestions = ""):
    MAX_RETRY = 3
    if suggestions != "":
        suggestions = "[IMPORTANT] Here are some suggestions for creating the workflow: " + suggestions
    agents = workflow_form.agents
    new_agents = []
    for agent in agents:
        if agent.category == "new":
            new_agents.append(agent)

    if len(new_agents) != 0:
        new_agent_str = "AGENT CREATION INSTRUCTIONS:\nBefore you create the workflow, you need to create the following new agents in the workflow:\n"
        for agent in new_agents:
            new_agent_str += f"Agent name: {agent.name}\nAgent description: {agent.description}\n"
            new_agent_str += f"Agent tools: {agent.tools}\n" if agent.tools else "Agent tools: []\n"
    else: 
        new_agent_str = ""

    def case_resolved(task_response: str, context_variables: dict): 
        """
        Use this tools when the desired workflow is created and tested successfully. You can NOT use this tool if the workflow is not created or tested successfully by running the workflow.
        """
        return f"Case resolved. The desired workflow is created and tested successfully.    : {task_response}"
    def case_not_resolved(task_response: str, context_variables: dict):
        """
        Use this tools when you encounter irresistible errors after trying your best with multiple attempts for creating the desired workflow. You can NOT use this tool before you have tried your best.
        """
        return f"Case not resolved. The desired workflow is not created or tested successfully. Details: {task_response}"
    workflow_creator_agent.functions.extend([case_resolved, case_not_resolved])
    messages.append({"role": "user", "content": f"""\
WORKFLOW CREATION INSTRUCTIONS:
The user's request to create workflow is: {requirements}
Given the completed workflow form with XML format: {output_xml_form}

TASK: 
Your task is to create the workflow for me, and then test the workflow by running the workflow using `run_workflow` tool to complete the user's task: 
{task}

{new_agent_str}

TERMINATION INSTRUCTIONS:
After you have created the workflow and tested it successfully, you can use the `case_resolved` tool to indicate the case is resolved, otherwise you should try your best to create the workflow. And ONLY after you have tried multiple times, you can use the `case_not_resolved` tool to indicate the case is not resolved and give the reason.

Remember: you can NOT stop util you have created the workflow and tested it successfully.
{suggestions}
"""})
    response = client.run(workflow_creator_agent, messages, context_variables, debug=debug)
    content = response.messages[-1]["content"]
    for i in range(MAX_RETRY):
        if content.startswith("Case resolved"):
            return content, messages
        messages.append({"role": "user", "content": f"""\
WORKFLOW CREATION INSTRUCTIONS:
The user's request to create workflow is: {requirements}
Given the completed workflow form with XML format: {output_xml_form}

TASK: 
Your task is to create the workflow for me, and then test the workflow by running the workflow using `run_workflow` tool to complete the user's task: 
{task}

{new_agent_str}

TERMINATION INSTRUCTIONS:
After you have created the workflow and tested it successfully, you can use the `case_resolved` tool to indicate the case is resolved, otherwise you should try your best to create the workflow. And ONLY after you have tried multiple times, you can use the `case_not_resolved` tool to indicate the case is not resolved and give the reason.

Remember: you can NOT stop util you have created the workflow and tested it successfully.

FEEDBACK:
The last attempt failed with the following error: {content}, please try again to create the desired workflow.
{suggestions}
"""})
        response = client.run(workflow_creator_agent, messages, context_variables, debug=debug)
        content = response.messages[-1]["content"]
    if i == MAX_RETRY:
        return f"The desired workflow is not created or tested successfully with {MAX_RETRY} attempts.", messages




def meta_workflow(model: str, context_variables: dict, debug: bool = True):
    print('\033[s\033[?25l', end='')  # Save cursor position and hide cursor
    logger = LoggerManager.get_logger()
    workflow_former = get_workflow_former_agent(model)
    workflow_creator_agent = get_workflow_creator_agent(model)

    agent = workflow_former
    agents = {workflow_former.name.replace(' ', '_'): workflow_former, workflow_creator_agent.name.replace(' ', '_'): workflow_creator_agent}
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#333333 #ffffff',
    })
    # 创建会话
    session = PromptSession(
        completer=UserCompleter(agents.keys()),
        complete_while_typing=True,
        style=style
    )

    client = MetaChain(log_path=logger)
    console = Console()
    messages = []

    last_message = "Tell me what do you want to create with `Workflow Chain`?"

    while True:
        query = session.prompt(
            f'{last_message} (type "exit" to quit, press "Enter" to continue): ',
            bottom_toolbar=HTML('<b>Prompt:</b> Enter <b>@</b> to mention Agents'), 
        )
        if query.strip().lower() == 'exit':
            
            logo_text = "Workflow Chain completed. See you next time! :waving_hand:"
            console.print(Panel(logo_text, style="bold salmon1", expand=True))
            break
        words = query.split()
        console.print(f"[bold green]Your request: {query}[/bold green]", end=" ")
        for word in words:
            if word.startswith('@') and word[1:] in agents.keys():
                # print(f"[bold magenta]{word}[bold magenta]", end=' ') 
                agent = agents[word.replace('@', '')]
            else:
                # print(word, end=' ')
                pass
        print()
        agent_name = agent.name
        console.print(f"[bold green][bold magenta]@{agent_name}[/bold magenta] will help you, be patient...[/bold green]")
        match agent_name:
            case "Workflow Former Agent":
                if query == "":
                    console.print(f"[bold red]There MUST be a request to create the agent form.[/bold red]")
                    continue
                requirements = query
                workflow_form, output_xml_form, messages = workflow_profiling(workflow_former, client, messages, context_variables, requirements, debug)
                if workflow_form is None:
                    console.print(f"[bold red][bold magenta]@{agent_name}[/bold magenta] has not created workflow form successfully, please modify your requirements again.[/bold red]")
                    last_message = "Tell me what do you want to create with `Workflow Chain`?"
                    continue
                agent = workflow_creator_agent
                context_variables["workflow_form"] = workflow_form
                console.print(f"[bold green][bold magenta]@{agent_name}[/bold magenta] has created workflow form successfully with the following details:\n[/bold green][bold blue]{output_xml_form}[/bold blue]")
                last_message = "It is time to create the desired workflow, do you have any suggestions for creating the workflow?"
            case "Workflow Creator Agent":
                suggestions = query
                default_value='Come up with a task for the workflow to test your created workflow, and use `run_workflow` tool to test your created workflow.'  # 这里设置你想要的默认值
                task = session.prompt(
                'It is time to create the desired workflow, what task do you want to complete with the workflow? (Press Enter if none): ',
                
                )
                task = default_value if not task.strip() else task
                agent_response, messages = workflow_editing(workflow_creator_agent, client, messages, context_variables, workflow_form, output_xml_form, requirements, task, debug, suggestions)
                if agent_response.startswith("Case not resolved"):
                    console.print(f"[bold red][bold magenta]@{agent_name}[/bold magenta] has not created workflow successfully with the following error: {agent_response}[/bold red]")
                    agent = workflow_creator_agent
                else:
                    console.print(f"[bold green][bold magenta]@{agent_name}[/bold magenta] has created workflow successfully with the following details:\n[/bold green][bold blue]{agent_response}[/bold blue]")
                    last_message = "Tell me what do you want to create with `Workflow Chain` next?"
    
    
    
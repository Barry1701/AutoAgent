from metachain import MetaChain
from metachain.util import UserCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from metachain.logger import LoggerManager, MetaChainLogger 
from rich.console import Console
from rich.panel import Panel
from metachain.agents.meta_agent.agent_former import get_agent_former_agent 
from metachain.agents.meta_agent.tool_editor import get_tool_editor_agent
from metachain.agents.meta_agent.agent_creator import get_agent_creator_agent
import re
from metachain.agents.meta_agent.form_complie import parse_agent_form

def extract_agents_content(text):
    pattern = r'(<agents>.*?</agents>)'
    # re.DOTALL 让 . 也能匹配换行符
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    return None

def agent_profiling(agent_former, client, messages, context_variables, requirements, debug): 
    messages.append({"role": "user", "content": requirements+ """
Directly output the form in the XML format without ANY other text.
"""})

    response = client.run(agent_former, messages, context_variables, debug=debug)
    output_xml_form = response.messages[-1]["content"]
    messages.extend(response.messages)
    agent_form = None

    MAX_RETRY = 3
    for i in range(MAX_RETRY):
        try:
            output_xml_form = extract_agents_content(output_xml_form)
            assert output_xml_form is not None, "No the XML form should be found in the output with the tag <agents>...</agents>."
            agent_form = parse_agent_form(output_xml_form)
            break
        except Exception as e:
            print(f"Error parsing XML to agent form: {e}. Retry {i+1}/{MAX_RETRY}")
            messages.append({"role": "user", "content": f"Error parsing XML to agent form: {e}\nNote that there are some special restrictions for creating agent form, please try again."})
            response = client.run(agent_former, messages, context_variables, debug=debug)
            output_xml_form = response.messages[-1]["content"]
            messages.extend(response.messages)
    return agent_form, output_xml_form, messages

def tool_editing(tool_editor_agent, client, messages, context_variables, agent_form, output_xml_form, debug, suggestions = ""):
    def case_resolved(task_response: str, context_variables: dict): 
        """
        Use this tools when ALL desired tools are created and tested successfully. You can NOT use this tool if tools are not created or tested successfully by running the tools.

        Args: 
            task_response: the response of creating the tool which contains the completion status of the tool.
        """
        return f"Case resolved. ALL desired tools are created and tested successfully. Details: {task_response}"
    def case_not_resolved(task_response: str, context_variables: dict):
        """
        Use this tools when you encounter irresistible errors after trying your best with multiple attempts for creating the desired tool. You can NOT use this tool before you have tried your best.

        Args: 
            task_response: the reason why the tool is not created or tested successfully.
        """
        return f"Case not resolved. Some desired tools are not created or tested successfully. Details: {task_response}"
    tool_editor_agent.functions.extend([case_resolved, case_not_resolved])
    MAX_RETRY = 3

    if suggestions != "":
        suggestions = "[IMPORTANT] Here are some suggestions for creating the tools: " + suggestions

    agents = agent_form.agents
    new_tools = []
    for agent in agents:
        if len(agent.tools.new) > 0:
            
            for idx, tool in enumerate(agent.tools.new):
                new_tools.append(f"{idx+1}. Tool name: {tool.name}, Tool description: {tool.description}")
    if len(new_tools) == 0:
        return "Case resolved. ALL desired tools are created and tested successfully.", messages
    new_tools_str = "\n".join(new_tools)
    messages.append({"role": "user", "content": f"""\
Your task is to create a list of new tools for me, the tools are:
{new_tools_str}
{suggestions}

Please create these new tools for me, note that you can NOT stop util you have created all the tools and tested them using `run_tool` successfully. 

If ALL tools are created and tested successfully, you can stop and use `case_resolved` tool. Otherwise, you should continue to create the tools. After you have tried your best, you can use `case_not_resolved` tool to give the reason why the tool is not created or tested successfully.

[IMPORTANT] ALL tools MUST be tested successfully by running the tools using `run_tool` before you stop.
"""})
    response = client.run(tool_editor_agent, messages, context_variables, debug=debug)
    content = response.messages[-1]["content"]
    for i in range(MAX_RETRY):
        if content.startswith("Case resolved"):
            return content, messages
        messages.append({"role": "user", "content": f"""\
Your task is to create a list of new tools for me, the tools are:
{new_tools_str}

Please create these new tools for me, note that you can NOT stop util you have created all the tools and tested them using `run_tool` successfully.
The last attempt failed with the following error: {content}, please try again to create the tools.
"""})
        response = client.run(tool_editor_agent, messages, context_variables, debug=debug)
        content = response.messages[-1]["content"]
    if i == MAX_RETRY:
        return f"{content}\nSome desired tools are not created or tested successfully with {MAX_RETRY} attempts.", messages
    
def agent_editing(agent_creator_agent, client, messages, context_variables, agent_form, output_xml_form, requirements, task, debug, suggestions = ""):
    MAX_RETRY = 3
    if suggestions != "":
        suggestions = "[IMPORTANT] Here are some suggestions for creating the agent(s): " + suggestions
    def case_resolved(task_response: str, context_variables: dict): 
        """
        Use this tools when the desired agent(s) is created and tested successfully. You can NOT use this tool if the agent(s) is not created or tested successfully by running the agent(s).
        """
        return f"Case resolved. The desired agent(s) is created and tested successfully.    : {task_response}"
    def case_not_resolved(task_response: str, context_variables: dict):
        """
        Use this tools when you encounter irresistible errors after trying your best with multiple attempts for creating the desired agent(s). You can NOT use this tool before you have tried your best.
        """
        return f"Case not resolved. The desired agent(s) is not created or tested successfully. Details: {task_response}"
    agent_creator_agent.functions.extend([case_resolved, case_not_resolved])
    messages.append({"role": "user", "content": f"""\
The user's request to create agent(s) is: {requirements}
Given the completed agent form with XML format: {output_xml_form}
After previous attempts, you have created new tools that required by the desired agent(s). 

Your task is to create the desired agent(s) for me, note that you may create ONE single agent or multiple agents connected by orchestrator agent.

After you have created the agent(s), you should test the agent(s) by running the agent(s) using `run_agent` tool to complete the user's task: 
{task}

Note that you can NOT stop util you have created the agent(s) and tested it successfully.
{suggestions}
"""})
    response = client.run(agent_creator_agent, messages, context_variables, debug=debug)
    content = response.messages[-1]["content"]
    for i in range(MAX_RETRY):
        if content.startswith("Case resolved"):
            return content, messages
        messages.append({"role": "user", "content": f"""\
The user's request to create agent(s) is: {requirements}
Given the completed agent form with XML format: {output_xml_form}
After previous attempts, you have created new tools that required by the desired agent(s). 

Your task is to create the desired agent(s) for me, note that you may create ONE single agent or multiple agents connected by orchestrator agent.

After you have created the agent(s), you should test the agent(s) by running the agent(s) using `run_agent` tool to complete the user's task: 
{task} 

Note that you can NOT stop util you have created the agent(s) and tested it successfully.
The last attempt failed with the following error: {content}, please try again to create the desired agent(s).
{suggestions}
"""})
        response = client.run(agent_creator_agent, messages, context_variables, debug=debug)
        content = response.messages[-1]["content"]
    if i == MAX_RETRY:
        return f"{content}\nThe desired agent(s) is not created or tested successfully with {MAX_RETRY} attempts.", messages
    
    
def meta_agent(model: str, context_variables: dict, debug: bool = True):
    logger = LoggerManager.get_logger()
    # generate agent form
    agent_former = get_agent_former_agent(model)
    tool_editor_agent = get_tool_editor_agent(model)
    agent_creator_agent = get_agent_creator_agent(model)
    # enter agent
    agent = agent_former
    agents = {agent_former.name.replace(' ', '_'): agent_former, tool_editor_agent.name.replace(' ', '_'): tool_editor_agent, agent_creator_agent.name.replace(' ', '_'): agent_creator_agent}
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

    last_message = "Tell me what do you want to create with `Agent Chain`?"
    
    while True:
        query = session.prompt(
            f'{last_message} (type "exit" to quit, press "Enter" to continue): ',
            bottom_toolbar=HTML('<b>Prompt:</b> Enter <b>@</b> to mention Agents'), 
        )
        if query.strip().lower() == 'exit':
            
            logo_text = "Agent Chain completed. See you next time! :waving_hand:"
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
            case 'Agent Former Agent':
                if query == "":
                    console.print(f"[bold red]There MUST be a request to create the agent form.[/bold red]")
                    continue
                requirements = query
                agent_form, output_xml_form, messages = agent_profiling(agent_former, client, messages, context_variables, requirements, debug)
                if agent_form is None:
                    console.print(f"[bold red]The agent form is not created successfully, please modify your requirements again.[/bold red]")
                    last_message = "Tell me what do you want to create with `Agent Chain`?"
                    continue
                
                agent = tool_editor_agent
                console.print(f"[bold green]The agent form is created successfully. [/bold green]")
                last_message = "It is time to create the desired tools, do you have any suggestions for creating the tools?"
            case 'Tool Editor Agent':
                suggestions = query
                tool_response, messages = tool_editing(tool_editor_agent, client, messages, context_variables, agent_form, output_xml_form, debug, suggestions)
                if tool_response.startswith("Case not resolved"):
                    console.print(f"[bold red]Some desired tools are not created or tested successfully, please try again.[/bold red]")
                    agent = tool_editor_agent
                    last_message = "The tools are not created successfully, do you have any suggestions for creating the tools?"
                    continue
                elif tool_response.startswith("Case resolved"):
                    agent = agent_creator_agent
                    console.print(f"[bold green]The tools are created successfully. [/bold green]")
                    last_message = "It is time to create the desired agent(s), do you have any suggestions for creating the agent(s)?"
                else: 
                    raise ValueError(f"Unknown tool response: {tool_response}")
                
            case 'Agent Creator Agent':
                suggestions = query
                default_value='Come up with a task for the agent(s) to test your created agent(s), and use `run_agent` tool to test your created agent(s).'  # 这里设置你想要的默认值
                task = session.prompt(
                'It is time to create the desired agent(s), what task do you want to complete with the agent(s)? (Press Enter if none): ',
                
                )
                task = default_value if not task.strip() else task
                agent_response, messages = agent_editing(agent_creator_agent, client, messages, context_variables, agent_form, output_xml_form, requirements, task, debug, suggestions)
                if agent_response.startswith("Case not resolved"):
                    console.print(f"[bold red]The agent(s) is not created or tested successfully, please try again.[/bold red]")
                    agent = agent_creator_agent
                    last_message = "The agent(s) are not created successfully, do you have any suggestions for creating the agent(s)?"
                    continue
                else:
                    console.print(f"[bold green]The agent(s) are created successfully. [/bold green]")
                    last_message = "Tell me what do you want to create with `Agent Chain`?"

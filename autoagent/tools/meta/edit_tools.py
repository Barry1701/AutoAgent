from autoagent.registry import registry
from autoagent.environment import LocalEnv, DockerEnv
from typing import Union
from autoagent.tools.terminal_tools import (
    create_file, 
    create_directory, 
    run_python, 
    print_stream, 
    terminal_page_up, 
    terminal_page_down, 
    terminal_page_to, 
    process_terminal_response
    )
from autoagent.registry import register_tool
import json
def get_metachain_path(env: Union[LocalEnv, DockerEnv]) -> str: 
    result = env.run_command('pip show autoagent')
    if result['status'] != 0:
        raise Exception("Failed to list tools. Error: " + result['result'])
    stdout = result['result']
    for line in stdout.split('\n'):
        if line.startswith('Editable project location:'):
            path = line.split(':', 1)[1].strip()
            return path
    raise Exception("Failed to list tools. The MetaChain is not installed in editable mode.")

def protect_tools(tool_name: str):
    if tool_name in registry.tools_info.keys():
        raise Exception(f"The tool `{tool_name}` can NOT be modified. You can DIRECTLY use the `{tool_name}` tool by USING the `run_tool` tool. Or you can create a new tool using this tool by `from autoagent.tools import {tool_name}`.")


@register_tool("list_tools")
def list_tools(context_variables): 
    """
    List all plugin tools in the MetaChain.
    Returns:
        A list of information of all plugin tools including name, args, docstring, body, return_type, file_path.
    """
    env: Union[LocalEnv, DockerEnv] = context_variables.get("code_env", LocalEnv())
    try:
        path = get_metachain_path(env)
    except Exception as e:
        return "Failed to list tools. Error: " + str(e)
    python_code = '"from autoagent.registry import registry; import json; print(\\"TOOL_LIST_START\\"); print(json.dumps(registry.display_plugin_tools_info, indent=4)); print(\\"TOOL_LIST_END\\")"'
    list_tools_cmd = f"cd {path} && DEFAULT_LOG=False python -c {python_code}"
    result = env.run_command(list_tools_cmd)
    if result['status'] != 0:
        return "Failed to list tools. Error: " + result['result']
    try:
        output = result['result']
        start_marker = "TOOL_LIST_START"
        end_marker = "TOOL_LIST_END"
        start_idx = output.find(start_marker) + len(start_marker)
        end_idx = output.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            return "Failed to parse tool list: markers not found"
            
        json_str = output[start_idx:end_idx].strip()
        return json_str
    except Exception as e:
        return f"Failed to process output: {str(e)}"
    # return result['result']
def check_tool_name(tool_name: str):
    if tool_name == "visual_question_answering":
        raise Exception("The tool `visual_question_answering` is not allowed to be modified. Directly use the `visual_question_answering` tool to handlen ANY visual tasks.")
@register_tool("create_tool")
def create_tool(tool_name: str, tool_code: str, context_variables): 
    """
    Create a plugin tool.
    Args:
        tool_name: The name of the tool.
        tool_code: The code of creating the tool. (You should strictly follow the format of the template given to you to create the tool.)
    Returns:
        A string representation of the result of the tool creation.
    """
    # try:
    #     check_tool_name(tool_name)
    # except Exception as e:
    #     return str(e)
    env: Union[LocalEnv, DockerEnv] = context_variables.get("code_env", LocalEnv())
    try:
        protect_tools(tool_name)
    except Exception as e:
        return "[ERROR] Failed to protect the tool `" + tool_name + "` with the following error: " + str(e)
    try:
        path = get_metachain_path(env)
    except Exception as e:
        return "[ERROR] Failed to list tools. Error: " + str(e)
    
    tools_dir = path + "/autoagent/tools"
    try:  
        tool_path = tools_dir + "/" + tool_name + ".py"
        if "from autoagent.registry import register_plugin_tool" not in tool_code:
            tool_code = "from autoagent.registry import register_plugin_tool\n" + tool_code
        msg = create_file(tool_path, tool_code, context_variables)
        
        if msg.startswith("Error creating file:"):
            return "[ERROR] Failed to create tool. Error: " + msg
        results = env.run_command(f'cd {path} && python {tool_path}')
        if results['status'] != 0:
            return "[ERROR] Failed to create tool. The python code of the tool is not correct. Error: " + results['result']
        return "[SUCCESS] Successfully created tool: " + tool_name + " in " + tools_dir + "/" + tool_name + ".py"
    except Exception as e:
        return "[ERROR] Failed to create tool. Error: " + str(e)

def tool_exists(tool_name: str, context_variables):
    try:
        list_res = list_tools(context_variables)
        tool_dict = json.loads(list_res)
        if tool_name not in tool_dict.keys():
            return False, tool_dict
        return True, tool_dict
    except Exception as e:
        return "Before deleting a tool, you should list all tools first. But the following error occurred: " + str(e), None

@register_tool("delete_tool")
def delete_tool(tool_name: str, context_variables): 
    """
    Delete a plugin tool.
    Args:
        tool_name: The name of the tool to be deleted.
    Returns:
        A string representation of the result of the tool deletion.
    """
    # try:
    #     check_tool_name(tool_name)
    # except Exception as e:
    #     return str(e)
    env: Union[LocalEnv, DockerEnv] = context_variables.get("code_env", LocalEnv())
    # try:
    #     exist_flag, tool_dict = tool_exists(tool_name, context_variables)
    #     if isinstance(exist_flag, str):
    #         return "Before deleting a tool, you should list all tools first. But the following error occurred: " + exist_flag
    #     if not exist_flag:
    #         return f"The tool `{tool_name}` does not exist."
    # except Exception as e:
    #     return "Before deleting a tool, you should list all tools first. But the following error occurred: " + str(e)
    try:
        protect_tools(tool_name)
    except Exception as e:
        return "[ERROR] Failed to delete the tool `" + tool_name + "` with the following error: " + str(e)
    list_res = list_tools(context_variables)
    tool_dict = json.loads(list_res)
    try:
        tool_path = tool_dict[tool_name]['file_path']
    except KeyError: 
        return "The tool `" + tool_name + "` does not exist."
    except Exception as e:
        return "Error: " + str(e)
    try:
        result = env.run_command(f"rm {tool_path}")
        if result['status'] != 0:
            return f"[ERROR] Failed to delete tool: `{tool_name}`. Error: " + result['result']
        return f"[SUCCESS] Successfully deleted tool: `{tool_name}`."
    except Exception as e:
        return f"[ERROR] Failed to delete tool: `{tool_name}`. Error: " + str(e)


@register_tool("run_tool")
@process_terminal_response
def run_tool(tool_name: str, run_code: str, context_variables): 
    """
    Run a tool with the given code.

    Args:
        tool_name: The name of the tool to be run.
        run_code: The code to be run.
    Returns:
        A string representation of the result of the tool running.
    """
    env: Union[LocalEnv, DockerEnv] = context_variables.get("code_env", LocalEnv())
    try:
        path = get_metachain_path(env)
    except Exception as e:
        return "Failed to get the path of the MetaChain. Error: " + str(e)
    # try:
    #     exist_flag, tool_dict = tool_exists(tool_name, context_variables)
    #     if isinstance(exist_flag, str):
    #         return "Before deleting a tool, you should list all tools first. But the following error occurred: " + exist_flag
    #     if not exist_flag:
    #         return f"The tool `{tool_name}` does not exist."
    # except Exception as e:
    #     return "Before testing a tool, you should list all tools first. But the following error occurred: " + str(e)
    
    test_dir = path + "/test_tools"

    try: 
        msg = create_directory(test_dir, context_variables)
        if msg.startswith("Error creating directory:"):
            return "[ERROR] Failed to create the test directory. Error: " + msg
    except Exception as e:
        return "[ERROR] Failed to create the test directory. Error: " + str(e)
    
    test_file_path = test_dir + "/" + "test_" + tool_name + ".py"
    try:
        msg = create_file(test_file_path, run_code, context_variables)
        if msg.startswith("Error creating file:"):
            return "[ERROR] Failed to create the test file. Error: " + msg
    except Exception as e:
        return "[ERROR] Failed to create the test file. Error: " + str(e)
    
    try:
        # result = run_python(context_variables, test_file_path, cwd=path, env_vars={"DEFAULT_LOG": "False"})
        # if "[SUCCESS]" not in result:
        #     return "[ERROR] Failed to test the tool. The test case is not correct. The result is: " + result
        # return f"The result is of the tool `{tool_name}`: \n{result.replace('[SUCCESS]', '')}"
        run_cmd = f"cd {path} && DEFAULT_LOG=False python {test_file_path}"
        result = env.run_command(run_cmd, print_stream)
        return result
    except Exception as e:
        return "[ERROR] Failed to test the tool. Error: " + str(e)

if __name__ == "__main__":
    # print(list_tools({}))
    # print(create_tool("visual_question_answering", "print('Hello, World!')", {}))
    test_code = """
from autoagent.tools import test_file_tools
print(test_file_tools())
"""
    print(run_tool("test_file_tools", test_code, {}))
    print(terminal_page_down())

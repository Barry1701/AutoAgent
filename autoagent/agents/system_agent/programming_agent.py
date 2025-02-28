from autoagent.types import Agent
from autoagent.tools import (
    gen_code_tree_structure, execute_command, read_file, create_file, write_file, list_files, create_directory, run_python, terminal_page_up, terminal_page_down, terminal_page_to
)
from autoagent.util import make_message, make_tool_message
from autoagent.registry import register_agent, register_plugin_agent
from constant import LOCAL_ROOT, DOCKER_WORKPLACE_NAME
from autoagent.environment import DockerEnv, BrowserEnv, LocalEnv
from typing import Union
from inspect import signature
def examples(context_variables):
    working_dir = context_variables.get("working_dir", None)
    examples_list = []
    examples_list.extend(make_message('user', "Create a list of numbers from 1 to 10, and display them in a web page at port 5000."))
    examples_list.extend(make_message('assistant', "I should first use create_file to write the python code into a file named 'app.py' for starting a web server"))
    examples_list.extend(make_tool_message(create_file, {'path': f"/{working_dir}/app.py", 
            'content': """
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    numbers = list(range(1, 11))
    return str(numbers)

if __name__ == '__main__':
    app.run(port=5000)"""}, f"File created at: /{working_dir}/app.py"))
    examples_list.extend(make_message('assistant', 'I have created a Python file `app.py` that will display a list of numbers from 1 to 10 when you run it. Let me run the Python file for you using `run_python`'))
    examples_list.extend(make_tool_message(run_python, {'code_path': f"/{working_dir}/app.py"}, f"""
Traceback (most recent call last):
  File "/{working_dir}/app.py", line 2, in <module>
    from flask import Flask
ModuleNotFoundError: No module named 'flask'"""))
    examples_list.extend(make_message('assistant', "It seems that Flask is not installed. Let me install Flask for you using `execute_command` by the command: pip install flask"))
    examples_list.extend(make_tool_message(execute_command, {'command': 'pip install flask'}, """Defaulting to user installation because normal site-packages is not writeable
Collecting flask
  Using cached flask-3.0.3-py3-none-any.whl (101 kB)
Collecting blinker>=1.6.2
  Using cached blinker-1.7.0-py3-none-any.whl (13 kB)
Collecting Werkzeug>=3.0.0
  Using cached werkzeug-3.0.2-py3-none-any.whl (226 kB)
Collecting click>=8.1.3
  Using cached click-8.1.7-py3-none-any.whl (97 kB)
Collecting itsdangerous>=2.1.2
  Using cached itsdangerous-2.2.0-py3-none-any.whl (16 kB)
Requirement already satisfied: Jinja2>=3.1.2 in /home/openhands/.local/lib/python3.10/site-packages (from flask) (3.1.3)
Requirement already satisfied: MarkupSafe>=2.0 in /home/openhands/.local/lib/python3.10/site-packages (from Jinja2>=3.1.2->flask) (2.1.5)
Installing collected packages: Werkzeug, itsdangerous, click, blinker, flask
Successfully installed Werkzeug-3.0.2 blinker-1.7.0 click-8.1.7 flask-3.0.3 itsdangerous-2.2.0"""))
    examples_list.extend(make_message('assistant', "Now that Flask is installed, let me run the Python file again using `run_python`"))
    examples_list.extend(make_tool_message(run_python, {'code_path': f"/{working_dir}/app.py"}, """* Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit"""))
    examples_list.extend(make_message('assistant', """The server is running on port 5000 with PID 124. You can access the list of numbers by visiting http://127.0.0.1:5000. Your task is completed."""))
    return examples_list

@register_agent(name= "Coding Agent", func_name="get_coding_agent")
@register_plugin_agent(name= "Coding Agent", func_name="get_coding_agent")
def get_coding_agent(model: str, **kwargs):
    def instructions(context_variables):
      code_env: Union[DockerEnv, LocalEnv] = context_variables.get("code_env", LocalEnv())
      return f"""You are a helpful programming assistant that can write and execute code. You are working in the folder: `{code_env.docker_workplace}`, and you can only access the files in this folder.

  Your can leverage your capabilities by using the specific functions listed below:

  1. Creating project structures based on the user requirement using function `create_directory`.
  2. Writing clean, efficient, and well-documented code using function `create_file` and `write_file`.
  3. You must run python scripts using function `run_python` rather than using the `execute_command` function.
  4. Exam the project to re-use the existing code snippets as much as possible, you may need to use
  functions like `list_files`, `read_file` and `write_file`.
  5. Writing the code into the file when creating new files, do not create empty files.
  6. Before you write code into the existing files, you should first read the file content using function `read_file` and reserve the original content as much as possible.
  7. Decide whether the task requires execution and debugging before moving to the next or not.
  8. Generate the commands to run and test the current task, and the dependencies list for this task.
  9. You only write Python scripts, don't write Jupiter notebooks which require interactive execution.
  10. Note that every path you read, write, or search should be the absolute path (starting with '/').
  11. If you should use programming other than Python, you should use the `write_file` function to write the code into a file, and then use the `execute_command` function to run the code.
  12. If the terminal output is too long, you should use `terminal_page_up` to move the viewport up, `terminal_page_down` to move the viewport down, `terminal_page_to` to move the viewport to the specific page of terminal where the meaningful content is.

  Note that you can use this agent to make complex computation, write a api request, and anything else that can be done by writing code.

  When you think you have completed the task the `System Triage Agent` asked you to do, you should use `transfer_back_to_triage_agent` to transfer the conversation back to the `System Triage Agent`. And you should not stop to try to solve the user's request by transferring to `System Triage Agent` only until the task is completed.

  [IMPORTANT] You can only complete the task by coding. Talk is cheap, show me the code with tools.
  """
    tool_list = [gen_code_tree_structure, execute_command, read_file, create_file, write_file, list_files, create_directory, run_python, terminal_page_up, terminal_page_down, terminal_page_to]
    
    return Agent(
    name="Coding Agent",
    model=model,
    instructions=instructions,
    functions=tool_list,
    # examples=examples,
    tool_choice = "required", 
    parallel_tool_calls = False
    )
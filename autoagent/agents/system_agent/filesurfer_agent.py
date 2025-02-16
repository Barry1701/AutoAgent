from autoagent.types import Agent
from autoagent.registry import register_agent
from autoagent.tools import open_local_file, page_up_markdown, page_down_markdown, find_on_page_ctrl_f, find_next, visual_question_answering
from autoagent.tools.file_surfer_tool import with_env
from autoagent.environment.markdown_browser import RequestsMarkdownBrowser
import time
from inspect import signature
from constant import LOCAL_ROOT, DOCKER_WORKPLACE_NAME
@register_agent(name = "File Surfer Agent", func_name="get_filesurfer_agent")
def get_filesurfer_agent(model: str = "gpt-4o", **kwargs):
    
    def handle_mm_func(tool_name, tool_args):
        return f"After using tool `{tool_name}({tool_args})`, I have opened the image I want to see and prepared a question according to the image. Please answer the question based on the image."
    def instructions(context_variables):
        file_env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
        assert file_env is not None, "file_env is required"
        return \
f"""
You are a file surfer agent that can handle local files.

You can only access the files in the folder `{file_env.docker_workplace}` and when you want to open a file, you should use absolute path from root like `{file_env.docker_workplace}/...`.

Note that `open_local_file` can read a file as markdown text and ask questions about it. And `open_local_file` can handle the following file extensions: [".html", ".htm", ".xlsx", ".pptx", ".wav", ".mp3", ".flac", ".pdf", ".docx"], and all other types of text files. 

But IT DOES NOT HANDLE IMAGES, you should use `visual_question_answering` to see the image. 

If the converted markdown text has more than 1 page, you can use `page_up`, `page_down`, `find_on_page_ctrl_f`, `find_next` to navigate through the pages.

When you think you have completed the task the `System Triage Agent` asked you to do, you should use `transfer_back_to_triage_agent` to transfer the conversation back to the `System Triage Agent`. And you should not stop to try to solve the user's request by transferring to `System Triage Agent` only until the task is completed.

If you are unable to open the file, you can transfer the conversation back to the `System Triage Agent`, and let the `Coding Agent` try to solve the problem by coding.
"""
    tool_list = [open_local_file, page_up_markdown, page_down_markdown, find_on_page_ctrl_f, find_next, visual_question_answering]
    return Agent(
        name="File Surfer Agent",
        model=model, 
        instructions=instructions,
        functions=tool_list,
        handle_mm_func=handle_mm_func,
        tool_choice = "required", 
        parallel_tool_calls = False
    )


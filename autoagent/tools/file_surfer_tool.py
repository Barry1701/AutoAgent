from autoagent.environment.markdown_browser import RequestsMarkdownBrowser
from autoagent.environment import LocalEnv
from functools import partial, update_wrapper
from inspect import signature
from typing import Tuple
import time
from autoagent.registry import register_tool, register_plugin_tool
from typing import Union, Optional
from typing import Optional
from autoagent.types import Result
import requests
import mimetypes
import base64
import uuid
import os
from litellm import completion
import cv2
import tempfile
from typing import List
from moviepy import *
import time
import base64
from faster_whisper import WhisperModel
from constant import COMPLETION_MODEL, API_BASE_URL

def with_env(env: RequestsMarkdownBrowser):
    """将env注入到工具函数中的装饰器"""
    def decorator(func):
        def wrapped(*args, **kwargs):
            return func(env=env, *args, **kwargs)
        
        # 保留原始函数的所有属性
        update_wrapper(wrapped, func)
        # 修改signature，移除env参数
        wrapped.__signature__ = signature(func).replace(
            parameters=[p for p in signature(func).parameters.values() if p.name != 'env']
        )
        return wrapped
    return decorator

def _get_browser_state(env: RequestsMarkdownBrowser) -> Tuple[str, str]:
    """
    Get the current state of the browser, including the header and content.
    """
    # print(env.address)
    header = f"Address: {env._convert_local_to_docker(env.address)}\n"
    # header = f"Address: {env.address}\n"

    if env.page_title is not None:
        header += f"Title: {env.page_title}\n"

    current_page = env.viewport_current_page
    total_pages = len(env.viewport_pages)

    address = env.address
    for i in range(len(env.history) - 2, -1, -1):  # Start from the second last
        if env.history[i][0] == address:
            header += f"You previously visited this page {round(time.time() - env.history[i][1])} seconds ago.\n"
            break
    prefix = f"Your browser is currently open to the page '{env.page_title}'\n" if env.page_title is not None else ""
    
    header = prefix + header
    header += f"Viewport position: Showing page {current_page+1} of {total_pages}.\n"
    return (header, env.viewport)

@register_tool("open_local_file")
def open_local_file(context_variables, path: str):
    """
    Open a local file at a path in the text-based browser and return current viewport content.

    Args:
        path: The absolute path of a local file to visit.
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    try: 
        # assert DOCKER_WORKPLACE_NAME in path, f"The path must be a absolute path from `/{DOCKER_WORKPLACE_NAME}/` directory"
        # local_path = path.replace('/' + DOCKER_WORKPLACE_NAME, LOCAL_ROOT + f'/{DOCKER_WORKPLACE_NAME}')
        # print(local_path)
        path = env._convert_docker_to_local(path)
        env.open_local_file(path)
        header, content = _get_browser_state(env)
        final_response = header.strip() + "\n=======================\n" + content
        return final_response
    except Exception as e:
        return f"Error in `open_local_file`: {e}"
    
@register_tool("page_up_markdown")
def page_up_markdown(context_variables):
    """
    Scroll the viewport UP one page-length in the current file and return the new viewport content.
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    try: 
        env.page_up()
        header, content = _get_browser_state(env)
        final_response = header.strip() + "\n=======================\n" + content
        return final_response
    except Exception as e:
        return f"Error in `page_up`: {e}"
    
@register_tool("page_down_markdown")
def page_down_markdown(context_variables):
    """
    Scroll the viewport DOWN one page-length in the current file and return the new viewport content.
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    try: 
        env.page_down()
        header, content = _get_browser_state(env)
        final_response = header.strip() + "\n=======================\n" + content
        return final_response
    except Exception as e:
        return f"Error in `page_down`: {e}"
    
@register_tool("find_on_page_ctrl_f")
def find_on_page_ctrl_f(context_variables, search_string: str):
    """
    Scroll the viewport to the first occurrence of the search string. This is equivalent to Ctrl+F.

    Args:
        search_string: The string to search for on the page. This search string supports wildcards like '*'
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    try: 
        env.find_on_page(search_string)
        header, content = _get_browser_state(env)
        final_response = header.strip() + "\n=======================\n" + content
        return final_response
    except Exception as e:
        return f"Error in `find_on_page_ctrl_f`: {e}"
    
@register_tool("find_next")
def find_next(context_variables):
    """
    Scroll the viewport to next occurrence of the search string.
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    try: 
        env.find_next()
        header, content = _get_browser_state(env)
        final_response = header.strip() + "\n=======================\n" + content
        return final_response
    except Exception as e:
        return f"Error in `find_next`: {e}" 

def _encode_image(context_variables, image_path: str):
    """
    Encode an image to base64.
    """
    env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
    assert env is not None, "file_env is not set"
    if image_path.startswith("http"):
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        request_kwargs = {
            "headers": {"User-Agent": user_agent},
            "stream": True,
        }

        # Send a HTTP request to the URL
        response = requests.get(image_path, **request_kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")

        extension = mimetypes.guess_extension(content_type)
        if extension is None:
            extension = ".download"
    
        fname = str(uuid.uuid4()) + extension
        download_path = os.path.abspath(os.path.join(env.local_workplace, "downloads", fname))

        with open(download_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=512):
                fh.write(chunk)

        image_path = download_path
    elif env.local_workplace in image_path:
        image_path = image_path
    else: 
        image_path = env._convert_docker_to_local(image_path)
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
# @register_tool("visual_question_answering")
# def visual_question_answering(context_variables, image_path: str, question: Optional[str] = None) -> Result:
#     """
#     A tool that can answer questions about attached images.
#     Args:
#         image_path: The path to the image on which to answer the question. This should be a local path to downloaded image.
#         question: the question to answer (default: "Please write a detailed caption for this image.")
#     """
#     env: RequestsMarkdownBrowser = context_variables.get("file_env", None)
#     assert env is not None, "file_env is not set"
#     try:
        
#         if not question:
#             question = "Please write a detailed caption for this image."
        
#         if not isinstance(image_path, str):
#             raise Exception("You should provide only one string as argument to this tool!")

#         base64_image = _encode_image(context_variables, image_path)

#         ret_str = question

#         msg = [{"role": "user", "content": [
#             {"type": "text", "text": question},
#             {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
#         ]}]
#         res = completion(model="gpt-4o-2024-08-06", messages=msg)
#         ret_str = res.choices[0].message.content
#         return Result(
#             value=ret_str,
#             # image=base64_image
#         )
#     except Exception as e:
#         return Result(
#             value=f"Error in `visual_question_answering`: {e}",
#         )

@register_tool("visual_question_answering")
@register_plugin_tool("visual_question_answering")
def visual_question_answering(context_variables, file_path: str, question: Optional[str] = None) -> Result:
    """
    This tool is used to answer questions about attached images or videos.
    Args:
        file_path: File path of the image or video.
        question: The question to answer (default: "Please describe the image or video content.")
    """
    env: Union[RequestsMarkdownBrowser, LocalEnv] = context_variables.get("file_env", LocalEnv())
    if env is None:
        env = LocalEnv()
    
    try:
        if not isinstance(file_path, str):
            raise Exception("File path must be a string!")

        # 判断文件类型
        file_extension = os.path.splitext(file_path)[1].lower()
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        if file_extension in video_extensions:
            # 视频处理逻辑
            if not question:
                question = "Please describe the video content."
                
            # 1. 提取关键帧
            local_file_path = env._convert_docker_to_local(file_path)
            base64Frames, audio_path = process_video(local_file_path)
            if audio_path is not None:
                audio_text = process_audio(audio_path)
            else:
                audio_text = "No audio found in the video."
            
            messages=[
            {"role": "system", "content":"""Use the video and transcription to answer the provided question."""},
            {"role": "user", "content": [
                {"type": "text", "text": "These are the frames from the video."},
                *map(lambda x: {"type": "image_url", 
                                "image_url": {"url": f'data:image/png;base64,{x}', "detail": "low"}}, base64Frames),
                {"type": "text", "text": f"The audio transcription is: {audio_text}\nQuestion: {question}"},
                ],
            }
            ]
            final_res = completion(model=COMPLETION_MODEL, messages=messages, base_url=API_BASE_URL)
            return Result(value=final_res.choices[0].message.content)
            
        else:
            # 原有的图片处理逻辑
            if not question:
                question = "Please describe the image content."
            
            base64_image = _encode_image(context_variables, file_path)
            msg = [{"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}]
            res = completion(model=COMPLETION_MODEL, messages=msg, base_url=API_BASE_URL)
            return Result(value=res.choices[0].message.content)
            
    except Exception as e:
        return Result(value=f"Error in `visual_question_answering`: {e}")
def process_audio(audio_path):
    model = WhisperModel("large-v3-turbo")
    print(f"Processing batch: {audio_path}")

    segments, info = model.transcribe(audio_path)
    transcribed_text = ""
    for segment in segments:
        transcribed_text += "[%.2fs -> %.2fs] %s\n" % (segment.start, segment.end, segment.text)

    return transcribed_text
def process_video(video_path, seconds_per_frame=2):
    base64Frames = []
    base_video_path, _ = os.path.splitext(video_path)

    video = cv2.VideoCapture(video_path)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video.get(cv2.CAP_PROP_FPS)
    frames_to_skip = int(fps * seconds_per_frame)
    curr_frame=0

    # Loop through the video and extract frames at specified sampling rate
    while curr_frame < total_frames - 1:
        video.set(cv2.CAP_PROP_POS_FRAMES, curr_frame)
        success, frame = video.read()
        if not success:
            break
        _, buffer = cv2.imencode(".png", frame)
        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))
        curr_frame += frames_to_skip
    video.release()

    # Extract audio from video
    
    clip = VideoFileClip(video_path)
    if clip.audio is not None:
        audio_path = f"{base_video_path}.mp3"
        clip.audio.write_audiofile(audio_path, bitrate="32k")
        clip.audio.close()
        clip.close()
    else:
        audio_path = None
        clip.close()

    print(f"Extracted {len(base64Frames)} frames")
    print(f"Extracted audio to {audio_path}")
    return base64Frames, audio_path
    
if __name__ == "__main__":
    local_root = os.getcwd()
    workplace_name = 'workplace_gaia_meta'
    env = RequestsMarkdownBrowser(viewport_size=1024 * 5, local_root=local_root, workplace_name=workplace_name, downloads_folder=os.path.join(local_root, workplace_name, "downloads"))
    # print("Open file", "~"*100)
    # print(open_local_file(env, f"/{workplace_name}/downloads/2207.01510v1.pdf"))
    # print("Page down", "~"*100)
    # print(page_down_markdown(env))
    # print("Find on page", "~"*100)
    # print(find_on_page_ctrl_f(env, "Chain-of-Thought"))
    # print("Find next", "~"*100)
    # print(find_next(env))
    print(visual_question_answering(context_variables = {"file_env": env}, file_path = "//workplace_gaia_meta/autoagent/downloaded_video.mp4", question="What is the highest number of bird species to be on camera simultaneously?").value)
    # print(visual_question_answering("/workplace_meta/downloads/workflow.png", "What is the main idea of this paper?").image)
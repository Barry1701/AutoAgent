# from autoagent.agents.programming_agent import get_programming_agent
# from autoagent.agents.tool_retriver_agent import get_tool_retriver_agent
# from autoagent.agents.agent_check_agent import get_agent_check_agent
# from autoagent.agents.tool_check_agent import get_tool_check_agent
# from autoagent.agents.github_agent import get_github_agent
# from autoagent.agents.programming_triage_agent import get_programming_triage_agent
# from autoagent.agents.plan_agent import get_plan_agent

# import os
# import importlib
# from autoagent.registry import registry

# # 获取当前目录下的所有 .py 文件
# current_dir = os.path.dirname(__file__)
# for file in os.listdir(current_dir):
#     if file.endswith('.py') and not file.startswith('__'):
#         module_name = file[:-3]
#         importlib.import_module(f'autoagent.agents.{module_name}')

# # 导出所有注册的 agent 创建函数
# globals().update(registry.agents)

# __all__ = list(registry.agents.keys())

import os
import importlib
from .staff_directory_agent import staff_directory_agent
from .camera_agent import camera_agent
from .doors_agent import doors_agent
from .operations_agent import operations_agent  # <-- DODANE


__all__ = [
    "staff_directory_agent",
    "camera_agent",
    "doors_agent",
    "operations_agent",  # <-- DODANE
]
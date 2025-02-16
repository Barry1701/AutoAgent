import os
import importlib
from autoagent.registry import registry

def import_workflows_recursively(base_dir: str, base_package: str):
    """Recursively import all workflows in .py files
    
    Args:
        base_dir: the root directory to start searching
        base_package: the base name of the Python package
    """
    for root, dirs, files in os.walk(base_dir):
        # get the relative path to the base directory
        rel_path = os.path.relpath(root, base_dir)
        
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                # build the module path
                if rel_path == '.':
                    # in the root directory
                    module_path = f"{base_package}.{file[:-3]}"
                else:
                    # in the subdirectory
                    package_path = rel_path.replace(os.path.sep, '.')
                    module_path = f"{base_package}.{package_path}.{file[:-3]}"
                
                try:
                    importlib.import_module(module_path)
                except Exception as e:
                    print(f"Warning: Failed to import {module_path}: {e}")

# get the current directory and import all tools
current_dir = os.path.dirname(__file__)
import_workflows_recursively(current_dir, 'autoagent.workflows')

# export all tool creation functions
globals().update(registry.workflows)

__all__ = list(registry.workflows.keys())
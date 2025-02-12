from autoagent.registry import register_tool
from huggingface_hub import HfApi, hf_hub_download
from typing import List
import tempfile
import os

@register_tool("search_trending_models_on_huggingface")
def search_trending_models_on_huggingface(pipeline_tag: str, limit: int = 5) -> str:
    """
    Search trending models on Hugging Face. Use this tool when you want to create a tool that uses Hugging Face models, only support the following tags: ['audio-text-to-text', 'text-to-image', 'image-to-image', 'image-to-video', 'text-to-video', 'text-to-speech', 'text-to-audio', 'automatic-speech-recognition', 'audio-to-audio'].
    
    Args:
        pipeline_tag: The pipeline tag you want to search on Hugging Face. ONLY support the following tags: ['audio-text-to-text', 'text-to-image', 'image-to-image', 'image-to-video', 'text-to-video', 'text-to-speech', 'text-to-audio', 'automatic-speech-recognition', 'audio-to-audio'].
        limit: The number of models you want to search on Hugging Face.
    Returns:
        A string representation of the information you found on Hugging Face.
    """
    # if pipeline_tag in ['image-text-to-text', 'visual-question-answering', 'video-text-to-text']:
    #     return f"As for the tags {pipeline_tag}, you should use `visual_question_answering` tool instead!"
    if pipeline_tag not in ['audio-text-to-text', 'text-to-image', 'image-to-image', 'image-to-video', 'text-to-video', 'text-to-speech', 'text-to-audio', 'automatic-speech-recognition', 'audio-to-audio']:
        return f"Only the following tags are supported: ['audio-text-to-text', 'text-to-image', 'image-to-image', 'image-to-video', 'text-to-video', 'text-to-speech', 'text-to-audio', 'automatic-speech-recognition', 'audio-to-audio']. If you want to use ['image-text-to-text', 'visual-question-answering', 'video-text-to-text'], you should use `visual_question_answering` tool instead!"
    api = HfApi()
    
    # 搜索模型和数据集
    models = api.list_models(pipeline_tag=pipeline_tag, limit=limit)
    
    # 格式化结果
    result = []
    
    # 添加模型信息
    result.append("Finding models on Hugging Face:")
    for model in models:
        result.append(f"- Model ID: {model.id}")
        
        # 收集模型信息
        info = []
        if model.card_data:
            if model.card_data.language:
                info.append(f"Language: {model.card_data.language}")
            if model.card_data.license:
                info.append(f"License: {model.card_data.license}")
            if model.card_data.library_name:
                info.append(f"Framework: {model.card_data.library_name}")
            if model.card_data.pipeline_tag:
                info.append(f"Task: {model.card_data.pipeline_tag}")
                
        if model.tags:
            info.append(f"Tags: {', '.join(model.tags)}")
        if model.downloads:
            info.append(f"Downloads(30 days): {model.downloads}")
            
        # 添加收集到的信息
        if info:
            result.append("  " + "\n  ".join(info))
            
        # 尝试获取README内容
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                readme_path = hf_hub_download(
                    repo_id=model.id,
                    filename="README.md",
                    repo_type="model",
                    local_dir=tmp_dir
                )
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                    # 提取前500个字符作为简介
                    summary = readme_content[:500].strip() + "..."
                    result.append("  Summary: " + summary.replace('\n', ' '))
        except Exception as e:
            result.append("  Summary: Failed to get")
            
        result.append("")
    
    return "\n".join(result)

@register_tool("get_hf_model_tools_doc")
def get_hf_model_tools_doc(model_id: str) -> str:
    """
    Get the detailed information of a model on Hugging Face, such as the detailed usage of the model containing the model's README.md. You should use this tool after you have used `search_trending_models_on_huggingface` to find the model you want to use.

    Args:
        model_id: The model id you want to get the detailed information on Hugging Face.
    Returns:
        A string representation of the detailed information of the model.
    """
    result = []
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            readme_path = hf_hub_download(
                repo_id=model_id,
                filename="README.md",
                repo_type="model",
                local_dir=tmp_dir
            )
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                summary = readme_content.strip()
                result.append("The detailed usage of the model is: " + summary)
    except Exception as e:
        result.append("Failed to get the detailed usage of the model. Error: " + str(e))
    return "\n".join(result)

if __name__ == "__main__":
    print(search_trending_models_on_huggingface("automatic-speech-recognition", limit=5))


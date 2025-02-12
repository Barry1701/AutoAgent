from autoagent.memory.tool_memory import ToolMemory, ToolReranker
import os
from autoagent.io_utils import get_file_md5
import pandas as pd
from autoagent.registry import register_tool
from constant import COMPLETION_MODEL, EMBEDDING_MODEL

@register_tool("get_api_plugin_tools_doc")
def get_api_plugin_tools_doc(query_text: str) -> str:
    """
    Retrieve satisfied tool documents based on the query text.
    Args:
        query_text: A query or request from users and you need to find the satisfied tool documents based on the query text.
    Returns:
        A string representation of the reranked results.
    """
    platform = 'default'
    tool_memory = ToolMemory(project_path = './code_db', db_name = ".tool_table_" + platform, platform=platform, api_key=os.getenv("OPENAI_API_KEY"), embedding_model=EMBEDDING_MODEL)
    # tool_reranker = ToolReranker(model="gpt-4o-2024-08-06")
    tool_reranker = ToolReranker(model=COMPLETION_MODEL)
    tool_path = "./tool_docs.csv"
    code_id = get_file_md5(tool_path)
    # print(code_id)
    tool_memory.collection_name = tool_memory.collection_name + f"_{code_id}"
    if tool_memory.count() == 0:
        tool_memory.add_dataframe(pd.read_csv(tool_path), batch_size=100)
    res_df = tool_memory.query_table(query_text, n_results=5)
    # print(res_df)
    try:
        reranked_result = tool_reranker.dummy_rerank(query_text, res_df)
    except Exception as e:
        return "Failed to rerank the tool documentation. Error: " + str(e)

    return reranked_result
    
if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = "AIzaSyDblGdaCwhWq0RpXe7aCPFQr0MBg__GN2E"
    print(get_api_plugin_tools_doc("Youtube"))
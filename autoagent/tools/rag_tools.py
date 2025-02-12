from autoagent.memory.rag_memory import Memory
import os
from autoagent.environment.docker_env import DockerEnv
from autoagent.environment.local_env import LocalEnv
from typing import Union
from autoagent.environment.local_env import LocalEnv
from autoagent.io_utils import compress_folder, get_file_md5
from autoagent.registry import register_tool, register_plugin_tool
from litellm import completion
import zipfile
import shutil
from autoagent.environment.markdown_browser.mdconvert import MarkdownConverter
from autoagent.memory.utils import chunking_by_token_size
import math
from autoagent.types import Result
# @register_tool("load_db")
# def load_db(db_path: str) -> str:

@register_tool("save_raw_docs_to_vector_db")
@register_plugin_tool("save_raw_docs_to_vector_db")
def save_raw_docs_to_vector_db(context_variables: dict, doc_name: str, saved_vector_db_name: str, overwrite: bool = False) -> Result:
    """
    Save the raw documents to the vector database. The documents could be: 
    - ANY text document with the extension of pdf, docx, txt, etcs.
    - A zip file containing multiple text documents
    - a directory containing multiple text documents
    All documents will be converted to raw text format and saved to the vector database in the chunks of 4096 tokens.
    
    Args:
        doc_name: The name of the raw documents. All documents will be stored in the the directory: /workplace/docs. 
        [NOTES] doc_name should  be the name of the file or directory, not the path to the file or directory, which means `docs/dir_name/` is not a valid doc_name.
        saved_vector_db_name: the name of collection you want to save the documents to.
        overwrite: Whether to overwrite the existing vector database when the vector database of the documents already exists. (default: False)
    """
    try:
        memo: Memory = context_variables.get("memo", Memory(project_path=os.path.join(os.getcwd(), "user_db"), db_name = ".user_db"))
        assert memo is not None, "memo is not set"
        code_env: Union[DockerEnv, LocalEnv] = context_variables.get("code_env", LocalEnv())
        assert code_env is not None, "code_env is not set"

        # check if the saved_vector_db_name is already in the vector database
        if memo.count(saved_vector_db_name) > 0:
            if overwrite:
                prefix_res = f"[WARNING] The collection `{saved_vector_db_name}` of the vector database already exists. Overwriting the existing collection."
            else: 
                return f"[WARNING] The collection `{saved_vector_db_name}` of the vector database already exists. Please set the overwrite flag to True if you want to overwrite the existing collection."
        else:
            prefix_res = ""

        doc_dir = os.path.join(code_env.local_workplace, "docs")
        os.makedirs(doc_dir, exist_ok=True)
        if doc_name.startswith("docs/"):
            doc_name = doc_name.replace("docs/", "")
        elif doc_name.startswith("/workspace/docs/"):
            doc_name = doc_name.replace("/workspace/docs/", "")
        doc_path = os.path.join(doc_dir, doc_name)
        assert os.path.exists(doc_path), f"The document `{doc_name}` does not exist in the directory `/workplace/docs`"
        # the doc_path is a directory
        if os.path.isdir(doc_path):
            file_list = []
            for file in os.listdir(doc_path):
                if file.endswith(('.pdf', '.docx', '.txt')):
                    file_list.append(os.path.join(doc_path, file))
        # the doc_path is a zip file
        elif os.path.isfile(doc_path) and (doc_path.endswith('.zip') or doc_path.endswith('.tar') or doc_path.endswith('.tar.gz')):
            file_name = os.path.splitext(doc_name)[0]
            extract_dir = os.path.join(doc_dir, file_name)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(doc_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 将提取的文件路径添加到file_list中
            file_list = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(('.pdf', '.docx', '.txt')):
                        file_list.append(os.path.join(root, file))
        # the doc_path is a single file
        elif os.path.isfile(doc_path):
            file_list.append(doc_path)
        else:
            raise ValueError(f"The document `{doc_name}` is not a valid file or directory")
        
        mdconvert = MarkdownConverter()
        
        ret_val = prefix_res
        batch_size = 200
        for file in file_list:
            queries = []
            doc_content = mdconvert.convert_local(file).text_content
            content_chunks = chunking_by_token_size(doc_content, max_token_size=4096)
            idx_list = ["chunk_" + str(chunk['chunk_order_index']) for chunk in content_chunks]
            for chunk in content_chunks:
                query = {
                    'query': chunk['content'],
                    'response': f"The {chunk['chunk_order_index']} chunk of the content of the file {file} is: \n{chunk['content']}"
                }
                queries.append(query)

            num_batches = math.ceil(len(queries) / batch_size)
        
            for i in range(num_batches):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, len(queries))
                batch_queries = queries[start_idx:end_idx]
                batch_idx = idx_list[start_idx:end_idx]
                
                # Add the current batch of queries
                memo.add_query(batch_queries, collection=saved_vector_db_name, idx=batch_idx)
            ret_val += f"The {file} has been added to the vector database `{saved_vector_db_name}`."
        context_variables["memo"] = memo
        return Result(
            value=ret_val,
            context_variables=context_variables
        )
    except Exception as e:
        ret_val = f"[ERROR] Failed to save the raw documents to the vector database: {e}"
        return ret_val

@register_tool("query_db")
@register_plugin_tool("query_db")
def query_db(context_variables: dict, query_text: str, saved_vector_db_name: str, n_results: int = 5) -> str:
    """
    Retrieve information from the database. Use this function when you need to search for information in the database.

    Args:
        query_text: The query to search for information in the database.
        saved_vector_db_name: The name of the vector database to search for information.
        n_results: The number of results to return. (default: 5)
    Returns:
        A string representation of the queried results.
    """
    try:
        memo: Memory = context_variables.get("memo", Memory(project_path=os.path.join(os.getcwd(), "user_db"), db_name = ".user_db"))
        assert memo is not None, "memo is not set"
        if memo.count(saved_vector_db_name) == 0:
            return f"[ERROR] The vector database `{saved_vector_db_name}` does not exist. Please use function `save_raw_docs_to_vector_db` to save the raw documents to the vector database."
        results = memo.query([query_text], collection=saved_vector_db_name, n_results=n_results)
            
        metadata_results = results['metadatas'][0]
        results = [item['response'] for item in metadata_results]
        ret_val = "\n".join(results)
    except Exception as e:
        ret_val = f"[ERROR] Failed to query the vector database: {e}"
    finally:
        return ret_val
    
@register_tool("modify_query")
@register_plugin_tool("modify_query")
def modify_query(what_you_know: str, query_text: str, **kwargs) -> str:
    """
    Modify the query based on what you know. Use this function when you need to modify the query to search for more relevant information.

    Args:
        what_you_know: The knowledge you have about the case.
        query_text: The original query.
    Returns:
        The modified query.
    """
    system_prompt = \
    f"""

    Assume you are an assistant searching for information. Now that you already know some knowledge ([What you know]), what sub-questions ([Modified query]) do you need to search for to help you answer the question ([Query]) you want to explore.

    Modify the query based on what you know, here is some example:
    Example 1:
    [What you know]: Alice and Bob have lunch together at 12:00 PM.
    [Query]: What did Alice and Bob do after the lunch?
    [Modified query]: What did Alice and Bob do after 12:00 PM?

    Example 2:
    [What you know]: Alice and Bob went to the cinema yesterday.
    [Query]: What did Alice and Bob do after the cinema?
    [Modified query]: What did Alice and Bob do yesterday?
    
    Return only 1 modified query.
    """
    
    user_prompt = f"""
    What you know: {what_you_know}
    Query: {query_text}
    Modified query:
    """
    create_params = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    response = completion(**create_params)
    modified_query = response.choices[0].message.content
    return f"The modified query is: {modified_query}. Now use function `query_db` to search the related information in the DataBase."



@register_tool("answer_query")
@register_plugin_tool("answer_query")
def answer_query(original_user_query: str, supporting_docs: str, **kwargs) -> str:
    """
    Answer the user query based on the supporting documents.

    Args:
        original_user_query: The original user query.
        supporting_docs: The supporting documents.
    Returns:
        The answer to the user query.
    """
    system_prompt = \
    f"""
    You are a helpful assistant. Answer the user query based on the supporting documents.  
    If you have not found the answer, say "Insufficient information."
    """
    
    user_prompt = f"""
    
    Here is the original user query and the supporting documents:
    Original user query: {original_user_query}
    Supporting documents: {supporting_docs}
    Answer:
    """
    create_params = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    response = completion(**create_params)
    answer = response.choices[0].message.content


    return answer


@register_tool("can_answer")
@register_plugin_tool("can_answer")
def can_answer(user_query: str, supporting_docs: str, **kwargs) -> str:
    """
    Check if you have enough information to answer the user query.

    Args:
        user_query: The user query.
        supporting_docs: The supporting documents.
    Returns:
        "True" if you have enough information to answer the user query, "False" otherwise.
    """
    system_prompt = \
    f"""
    You are a helpful assistant. Check if you have enough information to answer the user query.
    The answer should only be "True" or "False".
    """
    
    user_prompt = f"""
    
    Here is the original user query and the supporting documents:
    Original user query: {user_query}
    Supporting documents: {supporting_docs}
    Answer:
    """
    create_params = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    response = completion(**create_params)
    answer = response.choices[0].message.content
    
    return answer


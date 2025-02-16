import pandas as pd
from typing import List, Dict
from autoagent.memory.rag_memory import Memory, Reranker
import json
import math
import os
from litellm import completion
from pydantic import BaseModel
"""
Category | Tool_Name | Tool_Description | API_Name | API_Description | Method | API_Details | Required_API_Key | Platform
"""
class ToolMemory(Memory):
    def __init__(
        self,
        project_path: str,
        db_name: str = '.tool_table',
        platform: str = 'OpenAI',
        api_key: str = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        super().__init__(
            project_path=project_path,
            db_name=db_name,
            platform=platform,
            api_key=api_key,
            embedding_model=embedding_model
        )
        self.collection_name = 'tool_memory'

    def add_dataframe(self, df: pd.DataFrame, collection: str = None, batch_size: int = 100):
        if not collection:
            collection = self.collection_name
        queries = []
        for idx, row in df.iterrows():
            query = {
                'query': ' '.join(row[['Tool_Name', 'Tool_Description', 'API_Name', 'API_Description']].astype(str)),
                'response': row.to_json()
            }
            queries.append(query)
        
        # self.add_query(queries, collection=collection)
        print(f'Adding {len(queries)} queries to {collection} with batch size {batch_size}')
        num_batches = math.ceil(len(queries) / batch_size)
    
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(queries))
            batch_queries = queries[start_idx:end_idx]
            
            # Add the current batch of queries
            self.add_query(batch_queries, collection=collection)
            
            print(f"Batch {i+1}/{num_batches} added")

    def query_table(
        self, 
        query_text: str, 
        collection: str = None, 
        n_results: int = 5
    ) -> pd.DataFrame:
        """
        Query the table and return the results
        """
        if not collection:
            collection = self.collection_name
        results = self.query([query_text], collection=collection, n_results=n_results)
        
        metadata_results = results['metadatas'][0]
        
        df_results = pd.DataFrame([json.loads(item['response']) for item in metadata_results])
        return df_results

    def peek_table(self, collection: str = None, n_results: int = 20) -> pd.DataFrame:
        """
        Peek at the data in the table
        """
        if not collection:
            collection = self.collection_name
        results = self.peek(collection=collection, n_results=n_results)
        df_results = pd.DataFrame([json.loads(item['response']) for item in results['metadatas']])
        return df_results

class ToolReranker(Reranker):
    def rerank(self, query_text: str, query_df: pd.DataFrame) -> str:
        system_prompt = \
        """
        You are a helpful assistant that reranks the given API table based on the query.
        You should select the top 5 APIs to answer the query in the given format.
        You can only select APIs I give you.
        Directly give the answer without any other words.
        """
        # Use the DataFrame's to_dict method to convert all rows to a list of dictionaries
        # print('query_df', query_df)
        api_data = query_df.to_dict(orient='records')
        
        # Use a list comprehension and f-string to format each API's data
        api_prompts = [f"\n\nAPI {i+1}:\n{api}" for i, api in enumerate(api_data)]
        
        # add the query text to the prompt
        prompt = ''.join(api_prompts)
        prompt = f"The query is: {query_text}\n\n{prompt}"
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        class Tools(BaseModel):
            tool_name: str
            api_name: str
            rank: int

        class RerankResult(BaseModel):
            tools: list[Tools]
        
        create_params = {
            "model": self.model,
            "messages": message,
            "stream": False,
            "response_format": RerankResult
        }
        response = completion(**create_params).choices[0].message.content
        print(response)
        rerank_result = json.loads(response)["tools"]
        print(rerank_result)
        if len(rerank_result) == 0:
            return "Fail to retrieve the relevant information from the tool documentation."
        try:
            return self.wrap_rerank_result(rerank_result, query_df)
        except Exception as e:
            raise ValueError(f"Failed to wrap rerank result: {e}")
        
    def wrap_rerank_result(self, rerank_result: List[pd.DataFrame], query_df: pd.DataFrame) -> str:
        res = ""
        res_tmp = """
The rank {rank} referenced tool documentation is:
API Name: {api_name}
API Description: {api_description}
API Details: {api_details}
Required API Key: {required_api_key}
Platform: {platform}
"""
        try:
            for tool_api in rerank_result:
                tool_name = tool_api['tool_name']
                api_name = tool_api['api_name']
                matched_rows = query_df[(query_df['API_Name'] == api_name) & (query_df['Tool_Name'] == tool_name)]
                if not matched_rows.empty:
                    res = res + res_tmp.format(rank=tool_api['rank'], api_name=matched_rows['API_Name'].values[0], api_description=matched_rows['API_Description'].values[0], api_details=matched_rows['API_Details'].values[0], required_api_key=matched_rows['Required_API_Key'].values[0], platform=matched_rows['Platform'].values[0])
            return res
        except Exception as e:
            raise ValueError(f"Failed to wrap rerank result: {e}")
    def dummy_rerank(self, query_text: str, query_df: pd.DataFrame) -> str:
        res = ""
        res_tmp = """
The rank {rank} referenced tool documentation is:
API Name: {api_name}
API Description: {api_description}
API Details: {api_details}
Required API Key: {required_api_key}
Platform: {platform}
"""
        for i in range(len(query_df)):
            res = res + res_tmp.format(rank=i+1, api_name=query_df['API_Name'].values[i], api_description=query_df['API_Description'].values[i], api_details=query_df['API_Details'].values[i], required_api_key=query_df['Required_API_Key'].values[i], platform=query_df['Platform'].values[i])
        return res

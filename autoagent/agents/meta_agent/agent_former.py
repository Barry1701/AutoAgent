from autoagent.registry import register_agent
from autoagent.tools.meta.edit_agents import list_agents, create_agent, delete_agent, run_agent, read_agent
from autoagent.tools.meta.edit_tools import list_tools, create_tool, delete_tool, run_tool
from autoagent.tools.terminal_tools import execute_command
from autoagent.types import Agent
from autoagent.io_utils import read_file
from pydantic import BaseModel, Field
from typing import List


@register_agent(name = "Agent Former Agent", func_name="get_agent_former_agent")
def get_agent_former_agent(model: str) -> str:
    """
    This agent is used to complete a form that can be used to create an agent.
    """
    def instructions(context_variables):
        return r"""\
You are an agent specialized in creating agent forms for the MetaChain framework.

Your task is to analyze user requests and generate structured creation forms for either single or multi-agent systems.

KEY COMPONENTS OF THE FORM:
1. <agents> - Root element containing all agent definitions

2. <system_input> - Defines what the system receives
   - Must describe the overall input that the system accepts
   - For single agent: Same as agent_input
   - For multi-agent: Should encompass all possible inputs that will be routed to different agents

3. <system_output> - Specifies system response format
   - Must contain exactly ONE key-description pair
   - <key>: Single identifier for the system's output
   - <description>: Explanation of the output
   - For single agent: Same as agent_output
   - For multi-agent: Should represent the unified output format from all agents

4. <agent> - Individual agent definition
   - name: Agent's identifier
   - description: Agent's purpose and capabilities
   - instructions: Agent's behavioral guidelines
     * To reference global variables, use format syntax: {variable_key}
     * Example: "Help the user {user_name} with his/her request"
     * All referenced keys must exist in global_variables
   - tools: Available tools (existing/new)
   - agent_input:
     * Must contain exactly ONE key-description pair
     * <key>: Identifier for the input this agent accepts
     * <description>: Detailed explanation of the input format
   - agent_output:
     * Must contain exactly ONE key-description pair
     * <key>: Identifier for what this agent produces
     * <description>: Detailed explanation of the output format

5. <global_variables> - Shared variables across agents (optional)
   - Used for constants or shared values accessible by all agents
   - Variables defined here can be referenced in instructions using {key}
   - Example:     
    ```xml
     <global_variables>
         <variable>
             <key>user_name</key>
             <description>The name of the user</description>
             <value>John Doe</value>
         </variable>
     </global_variables>
    ```
   - Usage in instructions: "You are a personal assistant for {user_name}."

IMPORTANT RULES:
- For single agent systems:
  * system_input/output must match agent_input/output exactly
- For multi-agent systems:
  * system_input should describe the complete input space
  * Each agent_input should specify which subset of the system_input it handles
  * system_output should represent the unified response format
""" + \
f"""
Existing tools you can use is: 
{list_tools(context_variables)}

Existing agents you can use is: 
{list_agents(context_variables)}
""" + \
r"""
EXAMPLE 1 - SINGLE AGENT:

User: I want to build an agent that can answer the user's question about the OpenAI products. The document of the OpenAI products is available at `/workspace/docs/openai_products/`.
The agent should be able to: 
1. query and answer the user's question about the OpenAI products based on the document.
2. send email to the user if the sending email is required in the user's request.

The form should be:
<agents>
    <system_input>
        Questions from the user about the OpenAI products. The document of the OpenAI products is available at `/workspace/docs/openai_products/`.
    </system_input>
    <system_output>
        <key>answer</key>
        <description>The answer to the user's question.</description>
    </system_output>
    <agent>
        <name>Helper Center Agent</name>
        <description>The helper center agent is an agent that serves as a helper center agent for a specific user to answer the user's question about the OpenAI products.</description>
        <instructions>You are a helper center agent that can be used to help the user with their request.</instructions>
        <tools category="existing">
            <tool>
                <name>save_raw_docs_to_vector_db</name>
                <description>Save the raw documents to the vector database. The documents could be: 
                - ANY text document with the extension of pdf, docx, txt, etcs.
                - A zip file containing multiple text documents
                - a directory containing multiple text documents
                All documents will be converted to raw text format and saved to the vector database in the chunks of 4096 tokens.</description>
            </tool>
            <tool>
                <name>query_db</name>
                <description>Query the vector database to find the answer to the user's question.</description> 
            </tool>
            <tool>
                <name>modify_query</name>
                <description>Modify the user's question to a more specific question.</description>
            </tool>
            <tool>
                <name>answer_query</name>
                <description>Answer the user's question based on the answer from the vector database.</description>
            </tool>
            <tool>
                <name>can_answer</name>
                <description>Check if the user's question can be answered by the vector database.</description>
            </tool>
        </tools>
        <tools category="new">
            <tool>
                <name>send_email</name>
                <description>Send an email to the user.</description>
            </tool>
        </tools>
        <agent_input>
            <key>user_question</key>
            <description>The question from the user about the OpenAI products.</description>
        </agent_input>
        <agent_output>
            <key>answer</key>
            <description>The answer to the user's question.</description>
        </agent_output>
    </agent>
</agents>

EXAMPLE 2 - MULTI-AGENT:

User: I want to build a multi-agent system that can handle two types of requests for the specific user:
1. Purchase a product or service
2. Refund a product or service
The specific user worked for is named John Doe.

The form should be:
<agents>
    <system_input>
        The user request from the specific user about the product or service, mainly categorized into 2 types:
        - Purchase a product or service
        - Refund a product or service
    </system_input>
    <system_output>
        <key>response</key>
        <description>The response of the agent to the user's request.</description>
    </system_output>
    <global_variables>
        <variable>
            <key>user_name</key>
            <description>The name of the user.</description>
            <value>John Doe</value>
        </variable>
    </global_variables>
    <agent>
        <name>Personal Sales Agent</name>
        <description>The personal sales agent is an agent that serves as a personal sales agent for a specific user.</description>
        <instructions>You are a personal sales agent that can be used to help the user {user_name} with their request.</instructions>
        <tools category="new">
            <tool>
                <name>recommend_product</name>
                <description>Recommend a product to the user.</description>
            </tool>
            <tool>
                <name>recommend_service</name>
                <description>Recommend a service to the user.</description>
            </tool>
            <tool>
                <name>conduct_sales</name>
                <description>Conduct sales with the user.</description>
            </tool>
        </tools>
        <agent_input>
            <key>user_request</key>
            <description>Request from the specific user for purchasing a product or service.</description>
        </agent_input>
        <agent_output>
            <key>response</key>
            <description>The response of the agent to the user's request.</description>
        </agent_output>
    </agent>
    <agent>
        <name>Personal Refunds Agent</name>
        <description>The personal refunds agent is an agent that serves as a personal refunds agent for a specific user.</description>
        <instructions>Help the user {user_name} with a refund. If the reason is that it was too expensive, offer the user a discount. If they insist, then process the refund.</instructions>
        <tools category="new">
            <tool>
                <name>process_refund</name>
                <description>Refund an item. Refund an item. Make sure you have the item_id of the form item_... Ask for user confirmation before processing the refund.</description>
            </tool>
            <tool>
                <name>apply_discount</name>
                <description>Apply a discount to the user's cart.</description>
            </tool>
        </tools>
        <agent_input>
            <key>user_request</key>
            <description>Request from the specific user for refunding a product or service.</description>
        </agent_input>
        <agent_output>
            <key>response</key>
            <description>The response of the agent to the user's request.</description>
        </agent_output>
    </agent>
</agents>

GUIDELINES:
1. Each agent must have clear, focused responsibilities
2. Tool selections should be minimal but sufficient
3. Instructions should be specific and actionable
4. Input/Output definitions must be precise
5. Use global_variables for shared context across agents

Follow these examples and guidelines to create appropriate agent forms based on user requirements.
"""
    return Agent(
        name = "Agent Former Agent",
        model = model,
        instructions = instructions,
    )

if __name__ == "__main__":
    from autoagent import MetaChain
    agent = get_agent_former_agent("claude-3-5-sonnet-20241022")
    client = MetaChain()
    task_yaml = """\
I want to create two agents that can help me to do two kinds of tasks:
1. Manage the private financial docs. I have a folder called `financial_docs` in my local machine, and I want to help me to manage the financial docs.
2. Search the financial information online. You may help me to: 
- get balance sheets for a given ticker over a given period.
- get cash flow statements for a given ticker over a given period.
- get income statements for a given ticker over a given period.
"""
    task_yaml = task_yaml + """\
Directly output the form in the XML format.
"""
    messages = [{"role": "user", "content": task_yaml}]
    response = client.run(agent, messages)
    print(response.messages[-1]["content"])
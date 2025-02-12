from pydantic import BaseModel, Field, validator, field_validator, ValidationInfo
from typing import List, Dict, Optional, Literal
import xml.etree.ElementTree as ET

class KeyDescription(BaseModel):
    key: str
    description: str

class Tool(BaseModel):
    name: str
    description: str

class ToolSet(BaseModel):
    existing: List[Tool] = Field(default_factory=list)
    new: List[Tool] = Field(default_factory=list)

class GlobalVariable(BaseModel):
    key: str
    description: str
    value: str

class Agent(BaseModel):
    name: str
    description: str
    instructions: str
    tools: ToolSet
    agent_input: KeyDescription
    agent_output: KeyDescription

class AgentForm(BaseModel):
    system_input: str
    system_output: KeyDescription
    global_variables: Dict[str, GlobalVariable] = Field(default_factory=dict)
    agents: List[Agent]

    @field_validator('agents')
    def validate_single_agent_io(cls, v, info: ValidationInfo):
        """验证单agent系统的输入输出是否匹配"""
        if len(v) == 1:
            agent = v[0]
            system_output = info.data.get('system_output')
            if system_output and agent.agent_output.key != system_output.key:
                raise ValueError("Single agent system must have matching system and agent output keys")
        return v
    # def validate_global_ctx_instructions(cls, v, info: ValidationInfo):
    #     """验证全局变量和系统输入是否匹配"""

class XMLParser:
    @staticmethod
    def parse_key_description(elem: ET.Element, tag_name: str) -> KeyDescription:
        node = elem.find(tag_name)
        if node is None:
            raise ValueError(f"Missing {tag_name}")
        return KeyDescription(
            key=node.find('key').text.strip(),
            description=node.find('description').text.strip()
        )

    @staticmethod
    def parse_tools(agent_elem: ET.Element) -> ToolSet:
        tools = ToolSet()
        for tools_elem in agent_elem.findall('tools'):
            category = tools_elem.get('category')
            if category not in ('existing', 'new'):
                continue
            
            tool_list = []
            for tool_elem in tools_elem.findall('tool'):
                tool = Tool(
                    name=tool_elem.find('name').text.strip(),
                    description=tool_elem.find('description').text.strip()
                )
                tool_list.append(tool)
            
            if category == 'existing':
                tools.existing = tool_list
            else:
                tools.new = tool_list
        
        return tools

    @staticmethod
    def parse_global_variables(root: ET.Element) -> Dict[str, GlobalVariable]:
        variables = {}
        global_vars = root.find('global_variables')
        if global_vars is not None:
            for var in global_vars.findall('variable'):
                key = var.find('key').text.strip()
                variables[key] = GlobalVariable(
                    key=key,
                    description=var.find('description').text.strip(),
                    value=var.find('value').text.strip()
                )
        return variables

    @classmethod
    def parse_agent(cls, agent_elem: ET.Element) -> Agent:
        return Agent(
            name=agent_elem.find('name').text.strip(),
            description=agent_elem.find('description').text.strip(),
            instructions=agent_elem.find('instructions').text.strip(),
            tools=cls.parse_tools(agent_elem),
            agent_input=cls.parse_key_description(agent_elem, 'agent_input'),
            agent_output=cls.parse_key_description(agent_elem, 'agent_output')
        )

    @classmethod
    def parse_xml(cls, xml_content: str) -> AgentForm:
        root = ET.fromstring(xml_content)
        
        return AgentForm(
            system_input=root.find('system_input').text.strip(),
            system_output=cls.parse_key_description(root, 'system_output'),
            global_variables=cls.parse_global_variables(root),
            agents=[cls.parse_agent(agent_elem) for agent_elem in root.findall('agent')]
        )

def parse_agent_form(xml_content: str) -> Optional[AgentForm]:
    """
    读取并解析agent form XML文件
    
    Args:
        xml_content: XML文件内容
    
    Returns:
        解析后的AgentForm对象，如果解析失败返回None
    """
    try:
        # with open(xml_path, 'r', encoding='utf-8') as f:
        #     xml_content = f.read()
        
        return XMLParser.parse_xml(xml_content)
    
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

from pydantic import BaseModel, Field, field_validator, ValidationInfo, model_validator
from typing import List, Dict, Optional, Literal, Union
import xml.etree.ElementTree as ET
import re
# 基础模型

class WorkflowFormParseError(Exception):
    """Exception raised when WorkflowForm failed to parse.
    """

    def __init__(self, message):
        super().__init__(message)

class WorkflowConstraintError(Exception):
    """Exception raised when WorkflowForm failed to parse. Use this Exception to raise when the workflow form does not meet some specific constraints.
    """

    def __init__(self, message):
        super().__init__(message)

class KeyDescription(BaseModel):
    key: str
    description: str

class Tool(BaseModel):
    name: str
    description: str

class Action(BaseModel):
    type: Literal["RESULT", "ABORT", "GOTO"]
    value: Optional[str] = None

    @field_validator('value')
    def validate_goto_value(cls, v, info: ValidationInfo):
        if info.data.get('type') == 'GOTO' and not v:
            raise WorkflowConstraintError("GOTO action must have a value")
        return v

class Output(BaseModel):
    key: str
    description: str
    condition: Optional[str] = None
    action: Action

    @field_validator('condition')
    def validate_condition(cls, v, info: ValidationInfo):
        """验证condition的存在性"""
        outputs_info = info.data.get('_outputs_info', {})
        if outputs_info.get('multiple_outputs', False) and not v:
            raise WorkflowConstraintError("Multiple outputs must each have a condition")
        return v

class Event(BaseModel):
    name: str
    inputs: Optional[List[KeyDescription]] = None  # 修改这里
    task: Optional[str] = None  # 修改为可选
    outputs: List[Output]
    listen: Optional[List[str]] = None
    agent: Optional[Dict[str, str]] = None  # 修改为可选

    @field_validator('task')
    def validate_task(cls, v, info: ValidationInfo):
        """验证非on_start事件必须有task"""
        if info.data.get('name') != 'on_start' and not v:
            raise WorkflowConstraintError("Non-start events must have a task")
        return v
    @field_validator('agent')
    def validate_agent(cls, v, info: ValidationInfo):
        """验证非on_start事件必须有agent"""
        if info.data.get('name') != 'on_start' and not v:
            raise WorkflowConstraintError("Non-start events must have an agent")
        return v
    
    @field_validator('listen')
    def validate_listen(cls, v, info: ValidationInfo):
        """验证on_start事件不能有listen"""
        if info.data.get('name') == 'on_start' and v:
            raise WorkflowConstraintError("Start event cannot have listen elements")
        return v

    @field_validator('name')
    def validate_start_event(cls, v, info: ValidationInfo):
        """验证起始事件的名称"""
        if info.data.get('is_start_event', False) and v != "on_start":
            raise WorkflowConstraintError("Start event must be named 'on_start'")
        return v
    @field_validator('outputs')
    def validate_start_event_outputs(cls, v, info: ValidationInfo):
        """验证on_start事件的输出必须与输入相同"""
        if info.data.get('name') == 'on_start':
            inputs = info.data.get('inputs', [])
            if len(v) != len(inputs):
                raise WorkflowConstraintError("Start event outputs must match inputs")
            for output, input in zip(v, inputs):
                if output.key != input.key or output.description != input.description:
                    raise WorkflowConstraintError("Start event output must match input")
        return v

    @field_validator('outputs')
    def validate_outputs(cls, v):
        """验证输出的合法性"""
        result_outputs = [out for out in v if out.action.type == "RESULT"]
        if len(result_outputs) > 1:
            raise WorkflowConstraintError("Cannot have more than one RESULT type output")
        return v
    
    @model_validator(mode='after')
    def validate_event_constraints(self) -> 'Event':
        """验证事件的所有约束"""
        # 如果是 on_start event，跳过输入验证
        if self.name == "on_start":
            return self

        # 验证非on_start事件的输入
        if self.inputs is None:
            raise WorkflowConstraintError(f"Event '{self.name}': Non-start events must have inputs")

        # 验证listen是否存在
        if self.listen is None:
            raise WorkflowConstraintError(f"Event '{self.name}': Non-start events must have listen events")

        # 验证输入数量
        if len(self.inputs) != len(self.listen):
            raise WorkflowConstraintError(
                f"Event '{self.name}': Number of inputs ({len(self.inputs)}) must match number of listen events ({len(self.listen)})"
            )

        return self

class Agent(BaseModel):
    name: str
    description: str
    category: Literal["existing", "new"]
    tools: Optional[List[Tool]] = None

    @field_validator('tools')
    def validate_tools(cls, v, info: ValidationInfo):
        """验证tools的存在性"""
        if info.data.get('category') == 'existing' and v:
            raise WorkflowConstraintError("Existing agents should not have tools defined")
        return v

class WorkflowForm(BaseModel):
    name: str
    system_input: KeyDescription
    system_output: KeyDescription
    global_variables: Dict[str, str] = Field(default_factory=dict)
    agents: List[Agent]
    events: List[Event]

    @field_validator('events')
    def validate_events(cls, v):
        """验证事件流的合法性"""
        # 验证是否有且仅有一个on_start事件
        start_events = [e for e in v if e.name == "on_start"]
        if len(start_events) != 1:
            raise WorkflowConstraintError("Must have exactly one 'on_start' event")
        
        # 验证事件监听的合法性
        event_names = {e.name for e in v}
        for event in v:
            if event.listen:
                for listened_event in event.listen:
                    if listened_event not in event_names:
                        raise WorkflowConstraintError(f"Event {event.name} listens to non-existent event {listened_event}")
        return v
    @model_validator(mode='after')
    def validate_event_order(self) -> 'WorkflowForm':
        """验证事件的监听顺序：
        1. 事件只能监听在它之前定义的事件
        2. 不能有循环依赖
        """
        # 创建事件名称到索引的映射
        event_indices = {event.name: idx for idx, event in enumerate(self.events)}

        # 验证每个事件的监听关系
        for idx, event in enumerate(self.events):
            if event.listen:
                for listened_event_name in event.listen:
                    # 检查被监听的事件是否存在
                    if listened_event_name not in event_indices:
                        raise WorkflowConstraintError(
                            f"Event '{event.name}': Referenced listen event '{listened_event_name}' not found"
                        )
                    
                    # 检查是否监听了后面的事件
                    listened_idx = event_indices[listened_event_name]
                    if listened_idx >= idx:
                        raise WorkflowConstraintError(
                            f"Event '{event.name}' cannot listen to event '{listened_event_name}' "
                            f"because it appears later in the workflow or creates a cycle"
                        )

        return self

class XMLParser:
    @staticmethod
    def parse_key_description(elem: ET.Element) -> KeyDescription:
        return KeyDescription(
            key=elem.find('key').text.strip(),
            description=elem.find('description').text.strip()
        )

    @staticmethod
    def parse_action(elem: ET.Element) -> Action:
        action_elem = elem.find('action')
        return Action(
            type=action_elem.find('type').text.strip(),
            value=action_elem.find('value').text.strip() if action_elem.find('value') is not None else None
        )

    @staticmethod
    def parse_output(elem: ET.Element, multiple_outputs: bool) -> Output:
        return Output(
            key=elem.find('key').text.strip(),
            description=elem.find('description').text.strip(),
            condition=elem.find('condition').text.strip() if elem.find('condition') is not None else None,
            action=XMLParser.parse_action(elem),
            _outputs_info={'multiple_outputs': multiple_outputs}
        )

    @staticmethod
    def parse_event(elem: ET.Element, is_start: bool = False) -> Event:
        name = elem.find('name').text.strip()
        is_start = name == 'on_start'

        outputs_elem = elem.find('outputs')
        multiple_outputs = len(outputs_elem.findall('output')) > 1
        
        listen_elem = elem.find('listen')
        listen = [e.text.strip() for e in listen_elem.findall('event')] if listen_elem is not None and not is_start else None
        
        agent_elem = elem.find('agent')
        agent = {
            "name": agent_elem.find('name').text.strip(),
            "model": agent_elem.find('model').text.strip()
        } if agent_elem is not None and not is_start else None
        
        inputs_elem = elem.find('inputs')
        inputs = [XMLParser.parse_key_description(input_elem) 
                 for input_elem in inputs_elem.findall('input')] if inputs_elem is not None else None
        task_elem = elem.find('task')
        task = task_elem.text.strip() if task_elem is not None and not is_start else None

        return Event(
            name=name,
            inputs=inputs,
            task=task,
            outputs=[XMLParser.parse_output(out, multiple_outputs) 
                    for out in outputs_elem.findall('output')],
            listen=listen,
            agent=agent,
            is_start_event=is_start
        )

    @staticmethod
    def parse_agent(elem: ET.Element) -> Agent:
        tools_elem = elem.find('tools')
        tools = None
        if tools_elem is not None:
            tools = [Tool(
                name=tool.find('name').text.strip(),
                description=tool.find('description').text.strip()
            ) for tool in tools_elem.findall('tool')]

        return Agent(
            name=elem.find('name').text.strip(),
            description=elem.find('description').text.strip(),
            category=elem.get('category'),
            tools=tools
        )

    @classmethod
    def parse_xml(cls, xml_content: str) -> WorkflowForm:
        root = ET.fromstring(xml_content)
        workflow_name = root.get('name')
        if not workflow_name:
            # If name attribute doesn't exist, try to find name element
            name_elem = root.find('name')
            workflow_name = name_elem.text.strip() if name_elem is not None else "Unnamed Workflow"
        
        return WorkflowForm(
            name=workflow_name,
            system_input=cls.parse_key_description(root.find('system_input')),
            system_output=cls.parse_key_description(root.find('system_output')),
            global_variables={var.find('key').text.strip(): var.find('value').text.strip() 
                            for var in root.find('global_variables').findall('variable')} 
                            if root.find('global_variables') is not None else {},
            agents=[cls.parse_agent(agent) for agent in root.findall('.//agents/agent')],
            events=[cls.parse_event(event, event.find('name').text.strip() == 'on_start') 
                   for event in root.findall('.//events/event')]
        )
    
def extract_workflow_content(text):
    pattern = r'(<workflow>.*?</workflow>)'
    # re.DOTALL 让 . 也能匹配换行符
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        raise WorkflowFormParseError("The workflow XML form is not correct. The workflow XML form should be wrapped by <workflow>...</workflow> tags.")

def parse_workflow_form(xml_content: str) -> Optional[WorkflowForm]:
    """
    读取并解析workflow form XML文件
    
    Args:
        xml_content: XML文件内容
    
    Returns:
        解析后的WorkflowForm对象，如果解析失败返回None
    """
    try:
        workflow_content = extract_workflow_content(xml_content)
        return XMLParser.parse_xml(workflow_content)
    except WorkflowFormParseError as e:
        return f"The Error to extract workflow content: {e}"
    except WorkflowConstraintError as e:
        return f"The generated workflow form MUST meet all the constraints in the given instructions, but the constraints are not met: {e}"
    except ET.ParseError as e:
        return f"The Error parsing XML workflow form: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Optional, List, Tuple
import os
import json

# 提示词配置管理器,用于加载和管理不同类型的提示词
class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, dict]:
        prompts = {}
        
        base_prompts = self._load_json_file("base_prompts.json")
        if base_prompts:
            prompts.update(base_prompts)
        
        event_prompts = self._load_json_file("event_analyst.json")
        if event_prompts:
            prompts.update(event_prompts)
        
        return prompts
    
    def _load_json_file(self, filename: str) -> Optional[dict]:
        filepath = os.path.join(self.prompts_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"解析JSON模板文件 {filename} 失败: {e}")
                return None
        return None
    
    def get_prompt_template(self, prompt_name: str, **kwargs) -> ChatPromptTemplate:
        """
        获取指定名称的提示词模板，支持渲染占位符
        :param prompt_name: 模板名称
        :param kwargs: 模板占位符参数（如 message="事件信息"）
        :return: 渲染后的 ChatPromptTemplate
        """
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        if prompt_config.get("type") == "messages":
            # 构建消息模板列表
            message_templates: List[Tuple[str, str]] = []
            for msg in prompt_config.get("messages", []):
                role = msg["role"]
                content = msg["content"]
                
                if kwargs:
                    try:
                        content = content.format(** kwargs)
                    except KeyError as e:
                        print(f"模板 {prompt_name} 渲染失败：缺少占位符 {e}")
                
                message_templates.append((role, content))
            
            # 转换为LangChain标准的ChatPromptTemplate
            return ChatPromptTemplate.from_messages(message_templates)
        else:
            template = prompt_config.get("template", "")
            if kwargs:
                try:
                    template = template.format(**kwargs)
                except KeyError as e:
                    print(f"纯文本模板渲染失败：缺少占位符 {e}")
            return ChatPromptTemplate.from_template(template)
    
    def get_system_prompt(self, prompt_name: str) -> str:
        """获取指定模板中的系统提示词内容"""
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        for msg in prompt_config.get("messages", []):
            if msg.get("role") == "system":
                return msg.get("content", "")
        
        return ""
    
    def get_rendered_messages(self, prompt_name: str, **kwargs) -> List[SystemMessage | HumanMessage]:
        """
        直接渲染模板并返回可被模型调用的消息对象列表
        :return: [SystemMessage, HumanMessage, ...]
        """
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config or prompt_config.get("type") != "messages":
            raise ValueError(f"模板 {prompt_name} 不是合法的messages类型模板")
        
        rendered_messages = []
        for msg in prompt_config.get("messages", []):
            role = msg["role"]
            content = msg["content"]
            
            if kwargs:
                try:
                    content = content.format(** kwargs)
                except KeyError as e:
                    raise ValueError(f"渲染模板 {prompt_name} 失败：缺少占位符 {e}")
            
            # 转换为具体的消息对象
            if role == "system":
                rendered_messages.append(SystemMessage(content=content))
            elif role == "user":
                rendered_messages.append(HumanMessage(content=content))
        
        return rendered_messages

_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Optional
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
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_prompt_template(self, prompt_name: str, **kwargs) -> ChatPromptTemplate:
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        if prompt_config.get("type") == "messages":
            messages = []
            for msg in prompt_config.get("messages", []):
                messages.append((msg["role"], msg["content"]))
            return ChatPromptTemplate.from_messages(messages)
        else:
            return ChatPromptTemplate.from_template(prompt_config.get("template", ""))
    
    def get_system_prompt(self, prompt_name: str) -> str:
        prompt_config = self.prompts.get(prompt_name)
        if not prompt_config:
            raise ValueError(f"Prompt '{prompt_name}' not found")
        
        for msg in prompt_config.get("messages", []):
            if msg.get("role") == "system":
                return msg.get("content", "")
        
        return ""

_prompt_manager: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
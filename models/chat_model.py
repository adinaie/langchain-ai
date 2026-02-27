from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from prompts import PromptManager
import os
import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from typing import List, Annotated, Optional, Dict, Any
from typing_extensions import TypedDict

load_dotenv()

# 获取PromptManager单例
def get_prompt_manager() -> PromptManager:
    if not hasattr(get_prompt_manager, "instance"):
        get_prompt_manager.instance = PromptManager()
    return get_prompt_manager.instance

class ChatModel:
    def __init__(self, prompt_name: str = "default", checkpointer=None):
        # 创建自定义HTTP客户端
        self.http_client = httpx.Client(
            timeout=60,  # 增加超时时间到60秒
            verify=False,  # 禁用SSL验证（仅用于测试）
            follow_redirects=True,
        )
        
        # 初始化模型
        self.model = ChatOpenAI(
            model="Eccom-Coder",
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60,  # 增加超时时间到60秒
            http_client=self.http_client,
        )

        # 初始化提示词管理器和模板
        self.prompt_manager = get_prompt_manager()
        self.prompt_name = prompt_name
        self.prompt_template = self.prompt_manager.get_prompt_template(prompt_name)

        self.output_parser = StrOutputParser()
        
        # 定义状态结构
        class State(TypedDict):
            messages: Annotated[List[BaseMessage], add_messages]  # 明确类型为BaseMessage
        
        # 创建图
        graph_builder = StateGraph[State, None, State, State](State)
        
        # 聊天节点
        def chat_node(state: State):
            try:
                # 提取用户最新消息
                user_input = ""
                if state.get("messages"):
                    last_msg = state["messages"][-1]
                    if isinstance(last_msg, HumanMessage) and last_msg.content:
                        user_input = last_msg.content
                
                # 渲染提示词模板，获取完整的消息列表
                try:
                    rendered_messages = self.prompt_manager.get_rendered_messages(
                        prompt_name=self.prompt_name,
                        message=user_input
                    )
                except AttributeError:
                    rendered_messages = self.prompt_template.format_messages(message=user_input)
                
                full_messages = []
                for msg in rendered_messages:
                    if isinstance(msg, SystemMessage):
                        full_messages.append(msg)
                full_messages.extend([
                    msg for msg in state["messages"] 
                    if not isinstance(msg, SystemMessage)
                ])
                
                response = self.model.invoke(full_messages)
                
                return {"messages": [response if isinstance(response, BaseMessage) 
                                     else AIMessage(content=str(response))]}
            
            except Exception as e:
                print(f"Chat node execution error: {e}")
                return {"messages": [AIMessage(content="抱歉，处理您的请求时出错了。")]}
        
        # 添加节点
        graph_builder.add_node("chat", chat_node)
        
        # 设置入口点
        graph_builder.set_entry_point("chat")
        
        # 初始化检查点
        self.checkpointer = checkpointer or InMemorySaver()
        
        # 编译图，添加检查点
        self.graph = graph_builder.compile(checkpointer=self.checkpointer)
    
    def invoke(self, message: str, config: Optional[Dict[str, Any]] = None) -> str:
        if not message.strip():
            return "请输入有效的查询内容。"
        
        messages = [HumanMessage(content=message)]
        
        try:
            result = self.graph.invoke(
                {"messages": messages},
                config=config or {"configurable": {"thread_id": "default"}}
            )
            
            # 提取AI回复
            if result and isinstance(result, dict) and 'messages' in result:
                last_message = result['messages'][-1]
                if isinstance(last_message, BaseMessage):
                    return last_message.content or ""
                elif isinstance(last_message, dict) and 'content' in last_message:
                    return str(last_message['content'])
            
            return ""
        except Exception as e:
            print(f"Invoke error: {e}")
            return "抱歉，调用模型时发生错误。"
    
    async def astream(self, message: str, config: Optional[Dict[str, Any]] = None):
        if not message.strip():
            yield "请输入有效的查询内容。"
            return
        
        messages = [HumanMessage(content=message)]
        
        try:
            async for chunk in self.graph.astream(
                {"messages": messages},
                config=config or {"configurable": {"thread_id": "default"}},
                stream_mode="messages"
            ):
                content = self._extract_stream_content(chunk)
                if content:
                    yield content
        except Exception as e:
            print(f"Astream error: {e}")
            yield f"抱歉，流式调用模型时发生错误：{str(e)}"
    
    # 提取流式返回的内容
    def _extract_stream_content(self, chunk: Any) -> Optional[str]:
        if isinstance(chunk, tuple) and len(chunk) == 2:
            token = chunk[0]
            if isinstance(token, BaseMessage):
                return token.content or ""
            elif isinstance(token, str) and token.strip():
                return token
        
        elif isinstance(chunk, dict):
            if 'messages' in chunk and chunk['messages']:
                last_msg = chunk['messages'][-1]
                if isinstance(last_msg, BaseMessage):
                    return last_msg.content or ""
                elif isinstance(last_msg, dict):
                    return last_msg.get('content', "") or ""
        
        return None
    
    def close(self):
        """关闭HTTP客户端"""
        try:
            if self.http_client:
                self.http_client.close()
                self.http_client = None
        except Exception as e:
            print(f"Close HTTP client error: {e}")
    
    def get_history(self, config: Optional[Dict[str, Any]] = None) -> List[BaseMessage]:
        """获取对话历史"""
        try:
            # 使用checkpointer直接获取历史
            config = config or {"configurable": {"thread_id": "default"}}
            checkpoint = self.checkpointer.get(config)
            if checkpoint and checkpoint.get("values"):
                return checkpoint["values"].get("messages", [])
            result = self.graph.invoke({"messages": []}, config=config)
            return result.get("messages", []) if isinstance(result, dict) else []
        except Exception as e:
            print(f"Error getting history: {e}")
            return []

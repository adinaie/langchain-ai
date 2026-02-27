from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.messages import SystemMessage, HumanMessage
from prompts import PromptManager
import os
import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from typing import  List, Annotated
from typing_extensions import TypedDict

load_dotenv()

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

        # 使用提示词管理器获取提示模板
        self.prompt_manager = PromptManager()
        self.prompt = self.prompt_manager.get_prompt_template(prompt_name)
        self.prompt_name = prompt_name

        # 创建输出解析器
        self.output_parser = StrOutputParser()
        
        # 定义状态结构
        class State(TypedDict):
            messages: Annotated[List, add_messages]
        
        # 创建图
        graph_builder = StateGraph(State)
        
        # 定义聊天节点
        def chat_node(state: State):
            # 构建完整的消息列表，包括系统消息和历史消息
            full_messages = []
            
            # 添加系统消息
            if self.prompt and hasattr(self.prompt, 'messages'):
                for msg_template in self.prompt.messages:
                    if msg_template.type == 'system':
                        # 获取系统消息内容
                        system_content = msg_template.prompt.template
                        # 创建SystemMessage对象
                        system_message = SystemMessage(content=system_content)
                        full_messages.append(system_message)
            
            # 添加历史消息
            full_messages.extend(state['messages'])
            
            # 调用模型
            response = self.model.invoke(full_messages)
            # 返回新消息
            return {"messages": [response]}
        
        # 添加节点
        graph_builder.add_node("chat", chat_node)
        
        # 设置入口点
        graph_builder.set_entry_point("chat")
        
        # 初始化检查点
        self.checkpointer = checkpointer or InMemorySaver()
        
        # 编译图，添加检查点
        self.graph = graph_builder.compile(checkpointer=self.checkpointer)
    
    def invoke(self, message: str, config=None) -> str:
        """同步调用模型"""
        # 使用HumanMessage对象表示用户消息，系统消息在chat_node中处理
        messages = [HumanMessage(content=message)]
        
        # 调用图，传入消息
        result = self.graph.invoke(
            {"messages": messages},
            config=config
        )
        # 提取AI回复
        if result and 'messages' in result:
            last_message = result['messages'][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                return last_message['content']
        return ""
    
    async def astream(self, message: str, config=None):
        """异步流式调用模型"""
        # 使用HumanMessage对象表示用户消息，系统消息在chat_node中处理
        messages = [HumanMessage(content=message)]
        
        # 流式调用图
        async for chunk in self.graph.astream(
            {"messages": messages},
            config=config,
            stream_mode="messages"
        ):
            # 处理流式返回的格式
            if isinstance(chunk, tuple) and len(chunk) == 2:
                # messages模式返回的是(LLM令牌, 元数据)元组
                token, metadata = chunk
                if token:
                    # 检查token类型
                    if hasattr(token, 'content'):
                        # 如果是AIMessageChunk对象，获取其content属性
                        if token.content:
                            yield token.content
                    else:
                        # 如果是字符串，直接返回
                        yield token
            elif isinstance(chunk, dict):
                # 兼容其他可能的返回格式
                if 'messages' in chunk and chunk['messages']:
                    last_message = chunk['messages'][-1]
                    if isinstance(last_message, dict) and last_message.get('role') == 'assistant' and 'content' in last_message:
                        yield last_message['content']
                    elif hasattr(last_message, 'content'):
                        # 如果是AIMessage对象，获取其content属性
                        yield last_message.content

    
    def close(self):
        """关闭HTTP客户端"""
        if self.http_client:
            self.http_client.close()
    
    def get_history(self, config=None):
        """获取对话历史"""
        try:
            # 调用graph，传入空消息，获取完整状态
            result = self.graph.invoke(
                {"messages": []},
                config=config
            )
            # 提取消息
            if result and 'messages' in result:
                return result['messages']
            return []
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
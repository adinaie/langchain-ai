from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from models.chat_model import ChatModel
import json
import uuid
from datetime import datetime

# 创建路由器
router = APIRouter()

# 初始化内存保存器作为检查点
checkpointer = InMemorySaver()

# 存储不同prompt_name对应的ChatModel实例
chat_models = {}

# 获取或创建ChatModel实例
def get_chat_model(prompt_name: str = "default"):
    if prompt_name not in chat_models:
        # 为每个prompt_name创建一个新的ChatModel实例
        chat_models[prompt_name] = ChatModel(prompt_name=prompt_name, checkpointer=checkpointer)
    return chat_models[prompt_name]

# 全局变量，用于保存对话历史，格式：{conversation_key: [messages]}
global_history = {}

# 全局变量，用于保存会话信息，格式：{id: {id, name, created_at, ...}}
global_conversations = {}

class ChatRequest(BaseModel):
    content: str
    stream: bool = False
    role: str = "user"
    prompt_name: str = "default"
    conversation_key: str

class ChatResponse(BaseModel):
    id: str
    message: dict
    status: str

class HistoryRequest(BaseModel):
    conversation_key: str

class HistoryResponse(BaseModel):
    messages: list

# 会话相关模型
class ConversationRequest(BaseModel):
    name: str

class ConversationUpdateRequest(BaseModel):
    name: str

class ConversationResponse(BaseModel):
    id: str
    name: str
    created_at: str

class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


# 聊天模型调用
@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        # 创建会话配置
        config = {
            "configurable": {
                "thread_id": request.conversation_key
            }
        }
        
        # 根据prompt_name获取对应的ChatModel实例
        current_chat_model = get_chat_model(request.prompt_name)
        
        if request.stream:
            async def generate():
                try:
                    full_content = ""
                    start_event = {
                        "event": "message_start",
                        "conversation_key": request.conversation_key,
                        "status": "streaming"
                    }
                    # SSE格式
                    yield f"data: {json.dumps(start_event)}\n\n"
                    
                    async for chunk in current_chat_model.astream(request.content, config):
                        if chunk:
                            full_content += chunk
                            message_event = {
                                "event": "agent_message",
                                "content": chunk,
                                "status": "streaming"
                            }
                            yield f"data: {json.dumps(message_event)}\n\n"
                    end_event = {
                        "event": "message_end",
                        "content": full_content,
                        "status": "success"
                    }
                    yield f"data: {json.dumps(end_event)}\n\n"
                    
                    # 将消息添加到全局历史, 按照前端渲染格式存储
                    if request.conversation_key not in global_history:
                        global_history[request.conversation_key] = []
                    global_history[request.conversation_key].append({
                        "id": str(uuid.uuid4()),
                        "message": {
                            "role": "user",
                            "content": request.content
                        },
                        "status": "success"
                      })
                    global_history[request.conversation_key].append({
                        "id": str(uuid.uuid4()),
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "status": "success"
                      })

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    error_detail = f"{type(e).__name__}: {str(e)}"
                    error_event = {
                        "event": "message_error",
                        "conversation_key": request.conversation_key,
                        "content": error_detail,
                        "status": "error"
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                finally:
                    pass
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        else:
            result = current_chat_model.invoke(request.content, config)
            message_id = str(uuid.uuid4())
            
            # 将消息添加到全局历史
            if request.conversation_key not in global_history:
                global_history[request.conversation_key] = []
            global_history[request.conversation_key].append({
                        "id": str(uuid.uuid4()),
                        "message": {
                            "role": "user",
                            "content": request.content
                        },
                        "status": "success"
                      })
            global_history[request.conversation_key].append({
                        "id": str(uuid.uuid4()),
                        "message": {
                            "role": "assistant",
                            "content": result
                        },
                        "status": "success"
                      })
            
            return ChatResponse(
                id=message_id,
                message={
                    "role": "assistant",
                    "content": result
                },
                status="success"
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 获取对话历史
@router.post("/history")
async def get_history(request: HistoryRequest):
    try:
        conversation_key = request.conversation_key
        try:
            conversation_key = request.conversation_key
            messages = global_history.get(conversation_key, [])
            return HistoryResponse(messages=messages)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HistoryResponse(messages=[])
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 清空对话历史
@router.post("/clear_history")
async def clear_history(request: HistoryRequest):
    try:
        conversation_key = request.conversation_key
        if conversation_key in global_history:
            del global_history[conversation_key]
            return {"status": "success", "message": "对话历史已清空"}
        else:
            return {"status": "success", "message": "对话历史不存在"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 创建会话
@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationRequest):
    try:
        id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        conversation = {
            "id": id,
            "name": request.name,
            "created_at": created_at
        }
        
        global_conversations[id] = conversation
        
        return ConversationResponse(**conversation)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 获取会话
@router.get("/conversations/{id}", response_model=ConversationResponse)
async def get_conversation(id: str):
    try:
        conversation = global_conversations.get(id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 更新会话
@router.put("/conversations/{id}", response_model=ConversationResponse)
async def update_conversation(id: str, request: ConversationUpdateRequest):
    try:
        conversation = global_conversations.get(id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        conversation["name"] = request.name
        global_conversations[id] = conversation
        
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 删除会话
@router.delete("/conversations/{id}")
async def delete_conversation(id: str):
    try:
        if id not in global_conversations:
            raise HTTPException(status_code=404, detail="会话不存在")
        del global_conversations[id]
        
        # 删除相关的对话历史
        keys_to_delete = []
        for key in global_history:
            if key == id:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del global_history[key]
        
        return {"status": "success", "message": "会话已删除"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

# 获取会话列表
@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations():
    try:
        if not global_conversations:
            id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            
            default_conversation = {
                "id": id,
                "name": "会话1",
                "created_at": created_at
            }
            
            global_conversations[id] = default_conversation
        
        conversations = list(global_conversations.values())
        conversations.sort(key=lambda x: x["created_at"], reverse=False)
        
        return ConversationListResponse(conversations=conversations)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_detail = f"{type(e).__name__}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)


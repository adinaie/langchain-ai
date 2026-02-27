import requests
import json

# 测试对话历史功能
def test_history_function():
    url = "http://localhost:8000/chat"
    headers = {"Content-Type": "application/json"}
    
    # 使用相同的conversation_key
    conversation_key = "conversation_1"
    
    print("=== 测试对话历史功能 ===")
    print(f"使用对话ID: {conversation_key}")
    print()
    
    # 第一轮对话
    print("=== 第一轮对话 ===")
    data1 = {
        "query": "你好，我叫张三",
        "stream": False,
        "conversation_key": conversation_key
    }
    response1 = requests.post(url, headers=headers, json=data1)
    print(f"状态码: {response1.status_code}")
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"AI回复: {result1['message']['content']}")
    print()
    
    # 第二轮对话
    print("=== 第二轮对话 ===")
    data2 = {
        "query": "今天天气怎么样？",
        "stream": False,
        "conversation_key": conversation_key
    }
    response2 = requests.post(url, headers=headers, json=data2)
    print(f"状态码: {response2.status_code}")
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"AI回复: {result2['message']['content']}")
    print()
    
    # 第三轮对话
    print("=== 第三轮对话 ===")
    data3 = {
        "query": "我叫什么名字？",
        "stream": False,
        "conversation_key": conversation_key
    }
    response3 = requests.post(url, headers=headers, json=data3)
    print(f"状态码: {response3.status_code}")
    if response3.status_code == 200:
        result3 = response3.json()
        print(f"AI回复: {result3['message']['content']}")
    print()
    
    # 获取对话历史
    print("=== 获取对话历史 ===")
    history_url = "http://localhost:8000/history"
    history_data = {
        "conversation_key": conversation_key
    }
    history_response = requests.post(history_url, headers=headers, json=history_data)
    print(f"状态码: {history_response.status_code}")
    if history_response.status_code == 200:
        history_result = history_response.json()
        print(f"对话历史消息数: {len(history_result['messages'])}")
        print("对话历史:")
        for i, msg in enumerate(history_result['messages']):
            print(f"{i+1}. {msg['role']}: {msg['content']}")

if __name__ == "__main__":
    test_history_function()

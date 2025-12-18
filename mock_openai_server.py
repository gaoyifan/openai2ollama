import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
import asyncio
import time

app = FastAPI()

MODELS = [
    {
        "id": "gpt-mock",
        "object": "model",
        "created": 1686935002,
        "owned_by": "openai"
    }
]

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": MODELS}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "gpt-mock")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    tools = body.get("tools", [])

    print(f"Received request: model={model}, stream={stream}, tools={len(tools)}")
    
    # Simple tool detection
    tool_calls = None
    if tools and messages and "weather" in messages[-1]["content"].lower():
        tool_calls = [
            {
                "id": "call_mock_123",
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "arguments": json.dumps({"location": "San Francisco, CA"})
                }
            }
        ]

    if stream:
        async def event_generator():
            chunk_id = f"chatcmpl-{int(time.time())}"
            
            if tool_calls:
                 # Initial chunk with role
                yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': None, 'tool_calls': [{'index': 0, 'id': tool_calls[0]['id'], 'type': 'function', 'function': {'name': tool_calls[0]['function']['name'], 'arguments': ''}}] }, 'finish_reason': None}]})}\n\n"
                
                # Argument chunks
                args = tool_calls[0]['function']['arguments']
                for i in range(0, len(args), 5):
                     yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': args[i:i+5]}}] }, 'finish_reason': None}]})}\n\n"
                     await asyncio.sleep(0.05)
                
                # Finish
                yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls'}]})}\n\n"
                yield "data: [DONE]\n\n"

            else:
                response_text = "This is a mock response from OpenAI."
                
                # Initial chunk with role
                yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]})}\n\n"
                
                # Content chunks
                for word in response_text.split():
                    yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {'content': word + ' '}, 'finish_reason': None}]})}\n\n"
                    await asyncio.sleep(0.05)
                
                # Finish
                yield f"data: {json.dumps({'id': chunk_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        if tool_calls:
             return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls
                    },
                    "finish_reason": "tool_calls"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            }
        else:
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a mock response from OpenAI.",
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from openai import AsyncOpenAI
import json
import time

app = FastAPI()

# Configuration
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:8001/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy")

client = AsyncOpenAI(
    base_url=OPENAI_API_BASE,
    api_key=OPENAI_API_KEY,
)

@app.get("/api/tags")
async def tags():
    try:
        models = await client.models.list()
        # Convert OpenAI models to Ollama format
        ollama_models = []
        for m in models.data:
            ollama_models.append({
                "name": m.id,
                "model": m.id,
                "modified_at": "2023-01-01T00:00:00Z", # Dummy
                "size": 0,
                "digest": "sha256:dummy",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "7B",
                    "quantization_level": "Q4_0"
                }
            })
        return {"models": ollama_models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/show")
async def show(request: Request):
    body = await request.json()
    model_name = body.get("name")
    if not model_name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    # Return dummy info
    return {
        "license": "MIT",
        "modelfile": "# Modelfile",
        "parameters": "stop \"\n\"",
        "template": "{{ .System }}\n{{ .Prompt }}",
        "details": {
            "parent_model": "",
            "format": "gguf",
            "family": "llama",
            "families": ["llama"],
            "parameter_size": "7B",
            "quantization_level": "Q4_0"
        }
    }

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    model = body.get("model")
    messages = body.get("messages", [])
    stream = body.get("stream", True) # Default to True in Ollama
    tools = body.get("tools", [])

    # Convert Ollama messages to OpenAI messages
    # Only need to check for images? Ollama supports images in 'images' field. OpenAI uses content list.
    # For now, simplistic conversion.
    openai_messages = []
    for msg in messages:
        openai_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Prepare OpenAI request args
    kwargs = {
        "model": model,
        "messages": openai_messages,
        "stream": stream,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        if stream:
            async def event_generator():
                stream_resp = await client.chat.completions.create(**kwargs)
                async for chunk in stream_resp:
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason
                    
                    response_obj = {
                        "model": model,
                        "created_at": "2023-01-01T00:00:00Z", # Dummy
                        "message": {
                            "role": "assistant",
                            "content": "",
                        },
                        "done": False 
                    }

                    if delta.content:
                        response_obj["message"]["content"] = delta.content
                        yield json.dumps(response_obj) + "\n"
                    
                    elif delta.tool_calls:
                        # Ollama streaming tool calls? 
                        # Ollama usually returns the full tool call in one go or accumulates it?
                        # The official python client accumulates.
                        # But for streaming API, we might need to send partials if Ollama supports it,
                        # or more likely, OpenAI sends partials but Ollama client expects... what?
                        # Ollama API docs say:
                        # "The message field will only contain the content of the message for the first response." 
                        # Wait, for tool calls:
                        # "tool_calls": [ ... ]
                        
                        # We will construct a minimal compatible chunk
                         for tc in delta.tool_calls:
                            # OpenAI sends partial arguments.
                            # We might just forward what we have, but Ollama expects 'function' key directly inside tool_calls list items?
                            # OpenAI: tool_calls[i].function.arguments (string)
                            # Ollama: tool_calls[i].function.arguments (dict) - Wait, for streaming it might be different.
                            
                            # Let's check Ollama streaming behavior for tools with a quick search if needed, 
                            # but usually streaming tool calls is complex. 
                            # Let's try to just forward the raw structure but ensure keys match.
                            
                            # Actually, simplest logic for streaming tool calls from OpenAI to Ollama:
                            # OpenAI streams partial arg strings.
                            # Ollama client probably expects similar accumulation or complete objects.
                            # Let's look at the request requirement: "write a converter... support Tools and Streaming".
                            
                            # IMPORTANT: Ollama's streaming response for tool calls.
                            # Usually, if it's a tool call, done is False until strictly done.
                            # We'll pass the tool_calls structure.
                            # But we need to handle the OpenAI object to dict conversion.
                            
                            tc_dict = {
                                "index": tc.index,
                                "function": {}
                            }
                            if tc.id:
                                # Start of tool call
                                tc_dict["id"] = tc.id
                                tc_dict["type"] = "function"
                            
                            if tc.function:
                                if tc.function.name:
                                    tc_dict["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tc_dict["function"]["arguments"] = tc.function.arguments # String partial
                            
                            response_obj["message"]["tool_calls"] = [tc_dict]
                            yield json.dumps(response_obj) + "\n"

                    if finish_reason:
                        yield json.dumps({
                            "model": model, 
                            "created_at": "2023-01-01T00:00:00Z",
                            "message": {"role": "assistant", "content": ""},
                            "done": True, 
                            "total_duration": 0, 
                            "load_duration": 0, 
                            "prompt_eval_count": 0, 
                            "prompt_eval_duration": 0, 
                            "eval_count": 0, 
                            "eval_duration": 0
                        }) + "\n"

            return StreamingResponse(event_generator(), media_type="application/x-ndjson")
        
        else:
            resp = await client.chat.completions.create(**kwargs)
            message = resp.choices[0].message
            
            ollama_msg = {
                "role": message.role,
                "content": message.content or ""
            }
            
            if message.tool_calls:
                ollama_tool_calls = []
                for tc in message.tool_calls:
                    # Parse arguments string to dict for non-streaming response in Ollama
                    try:
                        args = json.loads(tc.function.arguments)
                    except:
                        args = tc.function.arguments # Fallback
                        
                    ollama_tool_calls.append({
                        "function": {
                            "name": tc.function.name,
                            "arguments": args
                        }
                    })
                ollama_msg["tool_calls"] = ollama_tool_calls

            return {
                "model": model,
                "created_at": "2023-01-01T00:00:00Z",
                "message": ollama_msg,
                "done": True,
                "total_duration": 0,
                "load_duration": 0,
                "prompt_eval_count": resp.usage.prompt_tokens,
                "prompt_eval_duration": 0,
                "eval_count": resp.usage.completion_tokens,
                "eval_duration": 0
            }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11434)

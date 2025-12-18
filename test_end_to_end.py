import ollama
import time
import sys

# Point to our converter
client = ollama.Client(host='http://127.0.0.1:11434')

def test_list_models():
    print("--- Testing List Models ---")
    try:
        response = client.list()
        print(f"Models found: {len(response['models'])}")
        # Inspect the first model object to see attributes
        if response['models']:
            first = response['models'][0]
            print(f"First model object type: {type(first)}")
            print(f"First model object dir: {dir(first)}")
            try:
                print(f" - {first.model}")
            except:
                print(f" - {first['model']}")

    except Exception as e:
        print(f"FAILED: {e}")

def test_chat_basic():
    print("\n--- Testing Chat (Basic) ---")
    try:
        response = client.chat(model='gpt-mock', messages=[
            {'role': 'user', 'content': 'Hello!'}
        ])
        print(f"Response: {response['message']['content']}")
    except Exception as e:
        print(f"FAILED: {e}")

def test_chat_streaming():
    print("\n--- Testing Chat (Streaming) ---")
    try:
        stream = client.chat(model='gpt-mock', messages=[
            {'role': 'user', 'content': 'Tell me a story'}
        ], stream=True)
        
        print("Stream output:", end=" ")
        for chunk in stream:
            print(chunk['message']['content'], end="", flush=True)
        print("\nDone.")
    except Exception as e:
        print(f"FAILED: {e}")
        # Print full exception for debugging
        import traceback
        traceback.print_exc()

def test_chat_tools():
    print("\n--- Testing Chat (Tools) ---")
    try:
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'get_current_weather',
                    'description': 'Get the current weather for a location',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'location': {
                                'type': 'string',
                                'description': 'The location to get the weather for, e.g. San Francisco, CA'
                            },
                        },
                        'required': ['location']
                    }
                }
            }
        ]
        
        # We need to trigger the mock server's tool capability.
        # The mock server checks for "weather" in content.
        response = client.chat(model='gpt-mock', messages=[
            {'role': 'user', 'content': 'What is the weather in San Francisco?'}
        ], tools=tools)
        
        print(f"Response has tool calls: {len(response['message'].get('tool_calls', []))}")
        if response['message'].get('tool_calls'):
            for tc in response['message']['tool_calls']:
                print(f"Tool Call: {tc['function']['name']} arguments: {tc['function']['arguments']}")
        else:
            print("No tool calls received.")
            print(response)

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Wait for servers to start
    print("Waiting for servers to be ready...")
    time.sleep(2)
    
    test_list_models()
    test_chat_basic()
    test_chat_streaming()
    test_chat_tools()

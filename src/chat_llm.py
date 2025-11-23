from ollama import chat
from typing import Any, Dict

model = "deepseek-r1:1.5b"  # or any other model you have downloaded


def generate_response(prompt: str) -> str:
    response = chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    # Handle common response shapes: dicts with 'message' or 'choices', otherwise stringify
    if isinstance(response, dict):
        if 'message' in response:
            return response['message']
        if 'choices' in response and isinstance(response['choices'], list) and response['choices']:
            first = response['choices'][0]
            if isinstance(first, dict):
                if 'message' in first:
                    return first['message']
                if 'text' in first:
                    return first['text']
    return str(response)

if __name__ == "__main__":
    test_prompt = "Hello, Expand on the benefits of using local LLMs for data privacy."
    print(generate_response(test_prompt))
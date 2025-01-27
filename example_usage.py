from lm_studio_agent import LMStudioAgent
import json
import sys

def main():
    try:
        # Try the standard LM Studio endpoint structure
        agent = LMStudioAgent(base_url="http://localhost:1234")
        # or alternatively:
        # agent = LMStudioAgent(base_url="http://127.0.0.1:1234")
        
        print(f"Attempting to connect to LM Studio at {agent.base_url}")
        
        # Simple test message
        system_prompt = "You are a helpful AI assistant."
        user_message = "Hi, are you there?"
        
        # Simple chat example
        response = agent.simple_chat(user_message, system_prompt)
        print("\nAI Response:", response)
        
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 
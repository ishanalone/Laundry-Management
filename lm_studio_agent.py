import requests
import json
import time

class LMStudioAgent:
    def __init__(self, base_url=None, port=None, max_retries=3, retry_delay=2):
        """
        Initialize the LM Studio agent with the base URL of the LM Studio server.
        
        Args:
            base_url (str, optional): Base URL for LM Studio API (e.g. "http://localhost")
            port (int, optional): Port number (default: 1234)
            max_retries (int): Maximum number of connection retry attempts
            retry_delay (int): Delay between retries in seconds
        """
        if port is not None and base_url is not None:
            self.base_url = f"{base_url.rstrip('/')}:{port}/v1"
        elif port is not None:
            self.base_url = f"http://localhost:{port}/v1"
        elif base_url is not None:
            self.base_url = f"{base_url.rstrip('/')}/v1"
        else:
            self.base_url = "http://localhost:1234/v1"
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.headers = {
            "Content-Type": "application/json"
        }
        
    def check_connection(self):
        """Check if LM Studio server is running and accessible"""
        for attempt in range(self.max_retries):
            try:
                # Try direct chat completion endpoint first
                test_url = f"{self.base_url}/chat/completions"
                response = requests.post(
                    test_url,
                    headers=self.headers,
                    json={
                        "messages": [{"role": "user", "content": "test"}],
                        "model": "local-model"
                    }
                )
                response.raise_for_status()
                return True
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    print(f"Connection attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                    print(f"Attempted URL: {test_url}")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(
                        "Could not connect to LM Studio. Please ensure that:\n"
                        "1. LM Studio is running\n"
                        "2. A model is loaded\n"
                        "3. The Runtime is selected in Settings\n"
                        f"4. The server URL is correct (trying: {test_url})\n"
                        "5. No firewall is blocking the connection\n\n"
                        f"Error details: {str(e)}"
                    )

    def chat_completion(self, messages, model="local-model", 
                       temperature=0.7, max_tokens=2000):
        """
        Send a chat completion request to LM Studio.
        
        Args:
            messages (list): List of message dictionaries with 'role' and 'content'
            model (str): Model identifier (default: "local-model")
            temperature (float): Sampling temperature (0.0 to 1.0)
            max_tokens (int): Maximum number of tokens to generate
            
        Returns:
            dict: The response from LM Studio
        """
        # Check connection before making request
        self.check_connection()
        
        endpoint = f"{self.base_url}/chat/completions"
        
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(endpoint, 
                                  headers=self.headers, 
                                  json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error communicating with LM Studio: {str(e)}")

    def simple_chat(self, message, system_prompt=None):
        """
        Simple interface for single-message chat interactions.
        
        Args:
            message (str): User message
            system_prompt (str, optional): System prompt to set context
            
        Returns:
            str: The model's response text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            response = self.chat_completion(messages)
            return response['choices'][0]['message']['content']
        except Exception as e:
            return f"Error: {str(e)}" 
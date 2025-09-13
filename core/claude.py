import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv

# Ensure the .env file is loaded to access the API key
load_dotenv()


class Claude:
    def __init__(self, model: str):
        # Initialize the client with OpenRouter's base URL and API key.
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model = model

    def add_user_message(self, messages: list, message): #function for sending user messages with the correct prompt to the LLM
        user_message: ChatCompletionMessageParam = {
            "role": "user",
            "content": message,
        }
        messages.append(user_message)

    def add_assistant_message(self, messages: list, message):
        assistant_message: ChatCompletionMessageParam = {
            "role": "assistant",
            "content": message,
        }
        messages.append(assistant_message)

    def text_from_message(self, message):
        return message.content

    def chat(
            self,
            messages: list,
            system: str | None = None,
            temperature: float = 1.0,
            stop_sequences: list[str] = [],
            tools=None,
            thinking=False,
            thinking_budget=1024,
    ):
        request_messages = []
        if system:
            request_messages.append({"role": "system", "content": system})
        request_messages.extend(messages)

        params = {
            "model": self.model,
            "messages": request_messages,
            "temperature": temperature,
            "stop": stop_sequences,
        }

        if tools:
            params["tools"] = tools

        response = self.client.chat.completions.create(**params)

        return response.choices[0].message
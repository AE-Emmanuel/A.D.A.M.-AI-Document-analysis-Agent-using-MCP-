from core.claude import Claude
from mcp_client import MCPClient
from core.tools import ToolManager
from openai.types.chat import ChatCompletionMessageParam


class Chat:
    def __init__(self, claude_service: Claude, clients: dict[str, MCPClient]):
        self.claude_service: Claude = claude_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[ChatCompletionMessageParam] = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(
        self,
        query: str,
    ) -> str:
        final_text_response = ""

        await self._process_query(query)

        while True:
            response_message = self.claude_service.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )

            # The response is now a message object. We add it directly to the message history.
            self.messages.append(response_message)

            if response_message.tool_calls:

                tool_result_parts = await ToolManager.execute_tool_requests(
                    self.clients, response_message # Pass the message object directly
                )

                # Add the tool result back to the messages list
                self.messages.extend(tool_result_parts)

            else:
                final_text_response = self.claude_service.text_from_message(
                    response_message
                )
                break

        return final_text_response
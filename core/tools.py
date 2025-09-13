import json
from typing import Optional, Literal, List
from mcp.types import CallToolResult, Tool, TextContent
from mcp_client import MCPClient

# 🚨 Import the correct message type from openai
from openai.types.chat import ChatCompletionMessage, ChatCompletionToolMessageParam


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[dict]:  # Return type is now list[dict]
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "type": "function",

                    # 2. Wrap the details in a "function" dictionary
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        # 3. Rename "input_schema" to "parameters" for compatibility
                        "parameters": t.inputSchema,
                    },
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
            cls, clients: list[MCPClient], tool_name: str
    ) -> Optional[MCPClient]:
        # This method is fine as it stands.
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                return client
        return None

    @classmethod
    def _build_tool_result_part(
            cls,
            tool_call_id: str,
            content: str,
            status: Literal["success"] | Literal["error"],  # This parameter is still useful for your internal logic
    ) -> ChatCompletionToolMessageParam:
        """Builds a tool result part dictionary."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }

    @classmethod
    async def execute_tool_requests(
            cls, clients: dict[str, MCPClient], message: ChatCompletionMessage  # Change type hint
    ) -> List[ChatCompletionToolMessageParam]:  #  Change return type
        """Executes a list of tool requests against the provided clients."""
        # This is the major change: iterate over tool_calls, not message.content
        tool_requests = message.tool_calls
        tool_result_blocks: list[ChatCompletionToolMessageParam] = []

        if not tool_requests:
            return []

        for tool_request in tool_requests:
            tool_call_id = tool_request.id
            tool_name = tool_request.function.name
            # 🚨 Tool arguments are now a JSON string
            tool_input = json.loads(tool_request.function.arguments)

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_part = cls._build_tool_result_part(
                    tool_call_id, "Could not find that tool", "error"
                )
                tool_result_blocks.append(tool_result_part)
                continue

            try:
                tool_output: CallToolResult | None = await client.call_tool(
                    tool_name, tool_input
                )
                items = []
                if tool_output:
                    items = tool_output.content
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)

                # status handling should be based on tool_output.isError
                status = "error" if tool_output and tool_output.isError else "success"

                tool_result_part = cls._build_tool_result_part(
                    tool_call_id,
                    content_json,
                    status,
                )
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                print(error_message)
                tool_result_part = cls._build_tool_result_part(
                    tool_call_id,
                    json.dumps({"error": error_message}),
                    "error",
                )
            tool_result_blocks.append(tool_result_part)

        return tool_result_blocks

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from mcp_client import MCPClient
from core.claude import Claude
from core.cli_chat import CliChat
from core.cli import CliApp

# Load environment variables and API keys
load_dotenv()
claude_model = os.getenv("MODEL", "")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

assert claude_model, "Error: MODEL cannot be empty. Update .env"
assert openrouter_api_key, "Error: OPENROUTER_API_KEY cannot be empty. Update .env"

async def main():
    """Initializes and runs the A.D.A.M. """
    print("🚀 Starting A.D.A.M. ...")
    
    claude_service = Claude(model=claude_model)
    clients = {}
    
    # Command to start the mcp_server in the background
    command, server_args = (
        ("uv", ["run", "mcp_server.py"])
        if os.getenv("USE_UV", "0") == "1"
        else ("python", ["mcp_server.py"])
    )

    async with AsyncExitStack() as stack:
        # Start and connect to the document server
        print("🔌 Connecting to MCP server...")
        doc_client = await stack.enter_async_context(
            MCPClient(command=command, args=server_args)
        )
        clients["doc_client"] = doc_client
        print("✅ Connected to MCP server!")

        # Initialize the agent and the command-line interface
        chat = CliChat(
            doc_client=doc_client,
            clients=clients,
            claude_service=claude_service,
        )
        
        cli = CliApp(chat)
        await cli.initialize()
        
        await cli.run()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())

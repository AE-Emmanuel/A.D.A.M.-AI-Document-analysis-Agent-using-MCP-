from typing import List, Tuple, Dict, Any
from pathlib import Path
import os
import json
from mcp.types import Prompt, PromptMessage
from anthropic.types import MessageParam

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient


class CliChat(Chat):
    def __init__(self, doc_client: MCPClient, clients: dict, claude_service: Claude):
        self.doc_client = doc_client
        self.clients = clients
        self.claude_service = claude_service
        self.messages = []  # Conversation history
        
        # System prompt that teaches the LLM about available tools and MCP prompts
        self.system_prompt = """You are name is ADAM which abbreviated AI Document analysis agent using MCP , an intelligent document assistant powered by MCP (Model Control Protocol). You can help users with document analysis, editing, formatting, summarization, and file operations.

AVAILABLE TOOLS:
DOCUMENT OPERATIONS:
- read_doc_contents(doc_id): Read the contents of a document by its ID
- edit_doc_contents(doc_id, old_str, new_str): Edit document content by replacing text
- upload_document(filename, content, file_path): Upload a document with optional advanced processing
- process_file_advanced(file_path, chunk_size): Process a file with metadata extraction and chunking

DOCUMENT ANALYSIS:
- get_document_metadata(doc_id): Get detailed metadata about a document (size, type, dates, etc.)
- get_document_chunks(doc_id, chunk_index): Get document content split into chunks
- search_documents(query, doc_ids, case_sensitive): Search across all documents for text patterns
- get_supported_file_types(): Get list of supported file types and processing capabilities

FILE OPERATIONS:
- list_files(pattern): List files in the working directory (e.g., "*.md", "*.py")
- read_file(file_path): Read a file from the working directory
- write_file(file_path, content): Write content to a file
- search_in_files(pattern, file_pattern): Search for text patterns in files
- set_working_directory(directory_path): Set the working directory for file operations

MCP PROMPTS AVAILABLE:
- find_and_load_project: Find project by marker file and load documents
- upload_directory: Upload all documents from a directory
- process_single_file: Process single file with advanced metadata
- show_document_metadata: Show detailed document metadata
- search_all_documents: Search across all documents
- show_document_chunks: Show document chunks
- show_supported_types: Show supported file types
- show_agent_status: Show current agent status
- summarize_document: Generate document summaries
- format_document: Reformat documents with better structure

DOCUMENT PROCESSING:
- Supports: .txt, .md, .py, .js, .html, .css, .pdf, .docx, .png, .jpg, .jpeg
- Automatic metadata extraction (file size, type, creation date, encoding, etc.)
- Document chunking for large files
- OCR processing for images
- PDF text extraction

BEHAVIOR GUIDELINES:
- When users mention documents with @filename (e.g., "@report.md"), use read_doc_contents with the filename as doc_id
- For file operations, use the appropriate file tools (read_file, write_file, etc.)
- Always call tools when you need information - don't guess or make assumptions
- For document analysis, use get_document_metadata to understand the document structure
- For large documents, consider using get_document_chunks to process in smaller pieces
- Use search_documents for finding specific information across multiple documents
- Be concise , On point and helpful in your responses
- Use tools systematically to accomplish complex tasks
- When processing requests that match MCP prompts, use the tools directly to fulfill the request

Remember: You have access to both individual tools and structured prompts. Use tools directly to accomplish user requests efficiently."""

    def _find_project_root(self, start_path: str = '.', marker: str = None) -> Path | None:
        """Scans upwards from the start_path to find a directory containing the marker file."""
        if not marker:
            return None
            
        current_dir = Path(start_path).resolve()
        
        while True:
            if (current_dir / marker).exists():
                return current_dir
            
            parent_dir = current_dir.parent
            if parent_dir == current_dir:  # Reached the filesystem root
                return None
            current_dir = parent_dir

    async def find_and_load_documents(self, marker: str):
        """Finds a project root based on a marker and loads documents from it."""
        print(f"🔎 Searching for directory containing '{marker}'...")
    
        project_path = self._find_project_root(marker=marker)
    
        if not project_path:
            print(f"❌ Directory not found. Could not find '{marker}' in this directory or any parent directories.")
            return

        print(f"✅ Directory found: {project_path}")
    
        # Find all supported documents in the discovered directory
        docs_to_load = [
            f for f in os.listdir(project_path) 
            if f.endswith((".txt", ".md", ".py", ".js", ".html", ".css", ".pdf", ".docx"))
        ]

        if not docs_to_load:
            print("No supported documents found in this directory.")
            return
        
        print("\nFound the following documents to load:")
        for doc in docs_to_load:
            print(f"  - {doc}")
            
        confirm = input("Load these documents for the session? (Y/n): ").lower()
        if confirm not in ['y', 'yes', '']:
            print("Loading cancelled.")
            return

        # Set working directory first
        try:
            await self.doc_client.call_tool('set_working_directory', {
                'directory_path': str(project_path)
            })
            print(f"📁 Working directory set to: {project_path}")
        except Exception as e:
            print(f"Warning: Could not set working directory: {e}")

        # Stream the contents of each document to the server with advanced processing
        for filename in docs_to_load:
            full_path = project_path / filename
            try:
                # Use advanced file processing for all supported file types
                await self.doc_client.call_tool('process_file_advanced', {
                    'file_path': filename,
                    'chunk_size': 2000
                })
                print(f"  -> ✅ Processed '{filename}' with metadata and chunking")
            except Exception as e:
                # Fallback to basic text processing
                try:
                    if filename.endswith((".txt", ".md")):
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        await self.doc_client.call_tool('upload_document', {
                            'filename': filename,
                            'content': content,
                            'file_path': str(full_path)
                        })
                        print(f"  -> ✅ Loaded '{filename}' (basic processing)")
                    else:
                        await self.doc_client.call_tool('upload_document', {
                            'filename': filename,
                            'content': f"Content of {filename} (advanced processing failed)",
                            'file_path': str(full_path)
                        })
                        print(f"  -> ⚠️  Registered '{filename}' (fallback processing)")
                except Exception as e2:
                    print(f"  ❌ Failed to load '{filename}': {e2}")
        
        print("\n🎉 All documents loaded successfully!")

    async def upload_directory(self, directory_path: str):
        """Upload all documents from a specified directory."""
        try:
            dir_path = Path(directory_path).resolve()
            
            if not dir_path.exists():
                print(f"❌ Directory '{directory_path}' does not exist.")
                return
                
            if not dir_path.is_dir():
                print(f"❌ '{directory_path}' is not a directory.")
                return

            print(f"📁 Scanning directory: {dir_path}")
            
            # Find all supported documents
            docs_to_load = []
            for ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.pdf', '.docx']:
                docs_to_load.extend(dir_path.glob(f'*{ext}'))
            
            if not docs_to_load:
                print("No supported documents found in this directory.")
                return
            
            print(f"\nFound {len(docs_to_load)} documents to load:")
            for doc in docs_to_load:
                print(f"  - {doc.name}")
            
            confirm = input("Load these documents? (Y/n): ").lower()
            if confirm not in ['y', 'yes', '']:
                print("Loading cancelled.")
                return

            # Set working directory
            await self.doc_client.call_tool('set_working_directory', {
                'directory_path': str(dir_path)
            })
            print(f"📁 Working directory set to: {dir_path}")

            # Load documents with advanced processing
            for doc_file in docs_to_load:
                try:
                    # Use advanced file processing for all supported file types
                    await self.doc_client.call_tool('process_file_advanced', {
                        'file_path': doc_file.name,
                        'chunk_size': 2000
                    })
                    print(f"  -> ✅ Processed '{doc_file.name}' with metadata and chunking")
                except Exception as e:
                    # Fallback to basic processing
                    try:
                        if doc_file.suffix in ['.txt', '.md']:
                            with open(doc_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            await self.doc_client.call_tool('upload_document', {
                                'filename': doc_file.name,
                                'content': content,
                                'file_path': str(doc_file)
                            })
                            print(f"  -> ✅ Loaded '{doc_file.name}' (basic processing)")
                        else:
                            await self.doc_client.call_tool('upload_document', {
                                'filename': doc_file.name,
                                'content': f"Binary file: {doc_file.name}",
                                'file_path': str(doc_file)
                            })
                            print(f"  -> ⚠️  Registered '{doc_file.name}' (fallback processing)")
                    except Exception as e2:
                        print(f"  ❌ Failed to load '{doc_file.name}': {e2}")
                    
            print("\n🎉 Directory upload complete!")
            
        except Exception as e:
            print(f"❌ Error uploading directory: {e}")

    async def process_single_file(self, file_path: str):
        """Process a single file with advanced metadata extraction"""
        try:
            result = await self.doc_client.call_tool('process_file_advanced', {
                'file_path': file_path,
                'chunk_size': 2000
            })
            print(f"✅ Successfully processed '{file_path}'")
            print(f"   File type: {result.get('file_type', 'unknown')}")
            print(f"   File size: {result.get('file_size', 0)} bytes")
            print(f"   Chunks: {result.get('chunk_count', 0)}")
        except Exception as e:
            print(f"❌ Error processing file '{file_path}': {e}")

    async def show_document_metadata(self, doc_id: str):
        """Show detailed metadata for a document"""
        try:
            metadata = await self.doc_client.call_tool('get_document_metadata', {
                'doc_id': doc_id
            })
            
            print(f"\n📄 Document Metadata: {doc_id}")
            print(f"   📁 Filename: {metadata.get('filename', 'N/A')}")
            print(f"   📊 File Type: {metadata.get('file_type', 'N/A')}")
            print(f"   📏 File Size: {metadata.get('file_size', 0):,} bytes")
            print(f"   🏷️  MIME Type: {metadata.get('mime_type', 'N/A')}")
            print(f"   📅 Created: {metadata.get('created_time', 'N/A')}")
            print(f"   📅 Modified: {metadata.get('modified_time', 'N/A')}")
            print(f"   🔤 Encoding: {metadata.get('encoding', 'N/A')}")
            print(f"   📄 Chunks: {metadata.get('chunk_count', 0)}")
            print(f"   📝 Content Length: {metadata.get('content_length', 0):,} characters")
            
            if metadata.get('page_count'):
                print(f"   📖 Pages: {metadata.get('page_count')}")
            if metadata.get('dimensions'):
                print(f"   📐 Dimensions: {metadata.get('dimensions')}")
            if metadata.get('language'):
                print(f"   🌐 Language: {metadata.get('language')}")
                
        except Exception as e:
            print(f"❌ Error getting metadata for '{doc_id}': {e}")

    async def search_documents(self, query: str):
        """Search across all documents for a query"""
        try:
            results = await self.doc_client.call_tool('search_documents', {
                'query': query,
                'case_sensitive': False
            })
            
            print(f"\n🔍 Search Results for: '{query}'")
            print(f"   📊 Total matches: {results.get('total_matches', 0)}")
            print(f"   📄 Documents found: {results.get('documents_found', 0)}")
            
            for result in results.get('results', []):
                print(f"\n   📄 {result.get('filename', 'Unknown')} ({result.get('doc_id', 'N/A')})")
                print(f"      Matches: {result.get('match_count', 0)}")
                
                # Show first few matches
                matches = result.get('matches', [])
                for i, match in enumerate(matches[:3]):  # Show first 3 matches
                    line = match.get('line', 0)
                    text = match.get('text', '')[:100]  # Truncate long matches
                    print(f"      Line {line}: ...{text}...")
                
                if len(matches) > 3:
                    print(f"      ... and {len(matches) - 3} more matches")
                    
        except Exception as e:
            print(f"❌ Error searching documents: {e}")

    async def show_document_chunks(self, doc_id: str):
        """Show document chunks"""
        try:
            chunks_info = await self.doc_client.call_tool('get_document_chunks', {
                'doc_id': doc_id
            })
            
            print(f"\n📄 Document Chunks: {doc_id}")
            print(f"   📊 Total chunks: {chunks_info.get('total_chunks', 0)}")
            
            chunks = chunks_info.get('chunks', [])
            for i, chunk in enumerate(chunks):
                print(f"\n   📝 Chunk {i + 1}/{len(chunks)} ({len(chunk)} characters):")
                # Show first 200 characters of each chunk
                preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
                print(f"      {preview}")
                
        except Exception as e:
            print(f"❌ Error getting chunks for '{doc_id}': {e}")

    async def show_supported_types(self):
        """Show supported file types and processing capabilities"""
        try:
            types_info = await self.doc_client.call_tool('get_supported_file_types', {})
            
            print(f"\n📋 Supported File Types:")
            extensions = types_info.get('supported_extensions', [])
            processors = types_info.get('processors_available', {})
            
            print(f"   📄 Extensions: {', '.join(extensions)}")
            print(f"\n   🔧 Processors Available:")
            for processor, available in processors.items():
                status = "✅" if available else "❌"
                print(f"      {status} {processor.upper()}")
                
        except Exception as e:
            print(f"❌ Error getting supported types: {e}")

    async def list_prompts(self) -> list[Prompt]:
        try:
            return await self.doc_client.list_prompts()
        except Exception as e:
            print(f"Error listing prompts: {e}")
            return []

    async def list_docs_ids(self) -> list[str]:
        try:
            return await self.doc_client.read_resource("docs://documents")
        except Exception as e:
            print(f"Error listing docs: {e}")
            return []

    async def get_doc_content(self, doc_id: str) -> str:
        try:
            return await self.doc_client.read_resource(f"docs://document/{doc_id}")
        except Exception as e:
            print(f"Error getting doc content: {e}")
            return ""

    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server and format them for the LLM"""
        try:
            tools = await self.doc_client.list_tools()
            
            # Convert MCP tools to OpenAI function calling format
            formatted_tools = []
            for tool in tools:
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                
                # Add parameters if they exist
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if isinstance(schema, dict):
                        if "properties" in schema:
                            formatted_tool["function"]["parameters"]["properties"] = schema["properties"]
                        if "required" in schema:
                            formatted_tool["function"]["parameters"]["required"] = schema["required"]
                
                formatted_tools.append(formatted_tool)
            
            return formatted_tools
        except Exception as e:
            print(f"Error getting tools: {e}")
            return []

    async def run(self, user_input: str) -> str:
        """Main agent loop - this is where the magic happens!"""
        try:
            print(f"🔧 Debug: Starting agent loop for: '{user_input}'")
            
            # Add user message to conversation history
            self.messages.append({"role": "user", "content": user_input})
            
            # Get available tools
            tools = await self._get_available_tools()
            print(f"🔧 Debug: Found {len(tools)} tools")
            
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                print(f"🔧 Debug: Agent iteration {iteration}")
                
                # Call ADAM with current messages and available tools
                response = self.claude_service.chat(
                    messages=self.messages,
                    system=self.system_prompt,
                    tools=tools,
                    temperature=0.1
                )
                
                print(f"🔧 Debug: Got response from Claude")
                print(f"🔧 Debug: Response has tool_calls: {hasattr(response, 'tool_calls') and response.tool_calls}")
                
                # Check if ADAM wants to call a function
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # ADAM wants to use a tool
                    self.messages.append({
                        "role": "assistant", 
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function", 
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                            } for tc in response.tool_calls
                        ]
                    })
                    
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        try:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            
                            print(f"🔧 Calling tool: {tool_name} with args: {tool_args}")
                            
                            # Call the tool via MCP
                            tool_result = await self.doc_client.call_tool(tool_name, tool_args)
                            print(f"🔧 Tool result: {str(tool_result)[:200]}...")
                            
                            # Add tool result to conversation
                            self.messages.append({
                                "role": "tool",
                                "content": str(tool_result),
                                "tool_call_id": tool_call.id
                            })
                            
                        except Exception as e:
                            print(f"❌ Tool call failed: {e}")
                            # Add error message as tool result
                            self.messages.append({
                                "role": "tool",
                                "content": f"Error: {str(e)}",
                                "tool_call_id": tool_call.id
                            })
                    
                    # Continue the loop to let the ADAM process the tool results
                    continue
                
                else:
                    # ADAM provided a final response without tool calls
                    final_response = response.content or "I couldn't generate a response."
                    print(f"🔧 Debug: Final response ready")
                    
                    # Add assistant response to conversation history
                    self.messages.append({"role": "assistant", "content": final_response})
                    
                    return final_response
            
            return "I reached the maximum number of iterations. Please try rephrasing your request."
            
        except Exception as e:
            error_msg = f"Error in agent loop: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            print(f"🔧 Debug traceback: {traceback.format_exc()}")
            return error_msg


def convert_prompt_message_to_message_param(
    prompt_message: "PromptMessage",
) -> MessageParam:
    role = "user" if prompt_message.role == "user" else "assistant"
    content = prompt_message.content

    if isinstance(content, dict) or hasattr(content, "__dict__"):
        content_type = (
            content.get("type", None)
            if isinstance(content, dict)
            else getattr(content, "type", None)
        )
        if content_type == "text":
            content_text = (
                content.get("text", "")
                if isinstance(content, dict)
                else getattr(content, "text", "")
            )
            return {"role": role, "content": content_text}

    if isinstance(content, list):
        text_blocks = []
        for item in content:
            if isinstance(item, dict) or hasattr(item, "__dict__"):
                item_type = (
                    item.get("type", None)
                    if isinstance(item, dict)
                    else getattr(item, "type", None)
                )
                if item_type == "text":
                    item_text = (
                        item.get("text", "")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    text_blocks.append({"type": "text", "text": item_text})

        if text_blocks:
            return {"role": role, "content": text_blocks}

    return {"role": role, "content": ""}
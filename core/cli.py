from typing import List, Optional
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
import os
from pathlib import Path
from core.cli_chat import CliChat


class SimpleCompleter(Completer):
    def __init__(self):
        self.resources = []
        # Add available commands
        self.commands = [
            'find', 'upload', 'process', 'metadata', 
            'search', 'chunks', 'types', 'status', 
            'quit', 'exit', 'q'
        ]
        # File extensions for autocompletion
        self.file_extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.pdf', '.docx', '.png', '.jpg', '.jpeg']
        # Common directory names
        self.common_dirs = ['docs', 'src', 'lib', 'tests', 'assets', 'images', 'data', 'config', 'scripts', 'build', 'dist']

    def update_resources(self, resources: List):
        self.resources = resources

    def get_completions(self, document, complete_event):
        text = document.text
        text_before_cursor = document.text_before_cursor
        
        # Handle / commands
        if text_before_cursor.startswith('/'):
            prefix = text_before_cursor[1:]  # Remove the /
            for cmd in self.commands:
                if cmd.startswith(prefix):  # Compare without the /
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display=cmd,
                        display_meta="Command"
                    )
            return
        
        # Handle @ mentions (existing code)
        if "@" in text_before_cursor:
            last_at_pos = text_before_cursor.rfind("@")
            prefix = text_before_cursor[last_at_pos + 1 :]

            for resource_id in self.resources:
                if resource_id.lower().startswith(prefix.lower()):
                    yield Completion(
                        resource_id,
                        start_position=-len(prefix),
                        display=resource_id,
                        display_meta="Document",
                    )
            return


class CliApp:
    def __init__(self, agent: CliChat):
        self.agent = agent
        self.resources = []

        self.completer = SimpleCompleter()

        self.kb = KeyBindings()

        @self.kb.add("@")
        def _(event):
            buffer = event.app.current_buffer
            buffer.insert_text("@")
            if buffer.document.is_cursor_at_the_end:
                buffer.start_completion(select_first=False)

        @self.kb.add("c-space")
        def _(event):
            """Ctrl+Space to trigger completion"""
            buffer = event.app.current_buffer
            buffer.start_completion(select_first=False)

        @self.kb.add("tab")
        def _(event):
            """Tab for indentation only"""
            buffer = event.app.current_buffer
            # Just insert tab - no completion
            buffer.insert_text("    ")
        

        self.history = InMemoryHistory()
        self.session = PromptSession(
            completer=self.completer,
            history=self.history,
            key_bindings=self.kb,
            style=Style.from_dict(
                {
                    "prompt": "#aaaaaa",
                    "completion-menu.completion": "bg:#222222 #ffffff",
                    "completion-menu.completion.current": "bg:#444444 #ffffff",
                }
            ),
            complete_while_typing=True,
        )

    async def initialize(self):
        await self.refresh_resources()

    async def refresh_resources(self):
        """Refresh the list of available documents for auto-completion"""
        try:
            self.resources = await self.agent.list_docs_ids()
            print(f"🔧 Debug: Found {len(self.resources)} documents for completion: {self.resources}")
            self.completer.update_resources(self.resources)
        except Exception as e:
            print(f"Error refreshing resources: {e}")
            self.resources = []
            self.completer.update_resources(self.resources)

    async def run(self):
        """The main interactive loop - PURE MCP with prompts"""
        print("🚀 Personal Agent is ready!")
        print("💡 Natural Language Commands:")
        print("   'find project with pyproject.toml'  - Find and load project")
        print("   'upload documents from ./docs'      - Upload directory")
        print("   'process file.pdf'                  - Process single file")
        print("   'show metadata for @doc.md'         - Show document metadata")
        print("   'search for API across documents'   - Search all documents")
        print("   'show chunks for @doc.md'           - Show document chunks")
        print("   'show supported file types'         - Show file type info")
        print("   'show status'                       - Show agent status")
        print("   'quit' or 'exit'                    - Exit application")

        
        try:
            while True:
                try:
                    user_input = await self.session.prompt_async("> ")
                    if not user_input.strip():
                        continue

                    # Handle quit commands
                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        print("👋 Goodbye!")
                        break
                    
                    # Check if input matches a prompt pattern and use MCP prompt
                    prompt_used = await self._try_use_mcp_prompt(user_input)
                    
                    if not prompt_used:
                        # Regular chat message - goes through AI agent
                        print("🤔 Processing...")
                        response = await self.agent.run(user_input)
                        print(f"\n✨ {response}\n")
                    # Refresh resources after any command that might have loaded documents
                    if any(keyword in user_input.lower() for keyword in ['find', 'upload', 'load', 'process']):
                        await self.refresh_resources()

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")

    async def _try_use_mcp_prompt(self, user_input: str) -> bool:
        """Try to match user input to MCP prompts and execute them"""
        input_lower = user_input.lower().strip()
        
        try:
            # Pattern matching for MCP prompts
            if input_lower.startswith('find') and ('project' in input_lower or 'marker' in input_lower):
                # Extract marker filename
                words = user_input.split()
                marker = words[-1] if len(words) > 1 else 'pyproject.toml'
                await self._use_mcp_prompt('find_and_load_project', {'marker_filename': marker})
                return True
                
            elif input_lower.startswith('upload') and ('directory' in input_lower or 'documents' in input_lower or 'from' in input_lower):
                # Extract directory path
                parts = user_input.split()
                directory = parts[-1] if len(parts) > 1 else './docs'
                await self._use_mcp_prompt('upload_directory', {'directory_path': directory})
                return True
                
            elif input_lower.startswith('process') and ('file' in input_lower):
                # Extract file path
                parts = user_input.split()
                file_path = parts[-1] if len(parts) > 1 else ''
                if file_path:
                    await self._use_mcp_prompt('process_single_file', {'file_path': file_path})
                    return True
                    
            elif 'metadata' in input_lower and '@' in user_input:
                # Extract doc_id from @mention
                doc_id = self._extract_doc_id(user_input)
                if doc_id:
                    await self._use_mcp_prompt('show_document_metadata', {'doc_id': doc_id})
                    return True
                    
            elif input_lower.startswith('search') and ('documents' in input_lower or 'across' in input_lower):
                # Extract search query
                query = user_input.replace('search for', '').replace('across documents', '').strip()
                if query:
                    await self._use_mcp_prompt('search_all_documents', {'query': query})
                    return True
                    
            elif 'chunks' in input_lower and '@' in user_input:
                # Extract doc_id from @mention
                doc_id = self._extract_doc_id(user_input)
                if doc_id:
                    await self._use_mcp_prompt('show_document_chunks', {'doc_id': doc_id})
                    return True
                    
            elif 'supported' in input_lower and ('types' in input_lower or 'file' in input_lower):
                await self._use_mcp_prompt('show_supported_types', {})
                return True
                
            elif input_lower.startswith('show status') or input_lower == 'status':
                await self._use_mcp_prompt('show_agent_status', {})
                return True
                
        except Exception as e:
            print(f"❌ Error using MCP prompt: {e}")
            
        return False

    async def _use_mcp_prompt(self, prompt_name: str, args: dict):
        """Execute an MCP prompt with the given arguments"""
        try:
            print(f"🎯 Using MCP prompt: {prompt_name}")
            
            # Get the prompt from MCP server
            prompt_messages = await self.agent.doc_client.get_prompt(prompt_name, args)
            
            # Convert prompt messages to regular messages and process through agent
            for prompt_msg in prompt_messages:
                # Convert prompt message to regular message format
                if hasattr(prompt_msg, 'content'):
                    content = prompt_msg.content
                    if hasattr(content, 'text'):
                        message_text = content.text
                    else:
                        message_text = str(content)
                else:
                    message_text = str(prompt_msg)
                
                print("🤔 Processing prompt...")
                response = await self.agent.run(message_text)
                print(f"\n✨ {response}\n")
                
        except Exception as e:
            print(f"❌ Error executing MCP prompt '{prompt_name}': {e}")

    def _extract_doc_id(self, text: str) -> str:
        """Extract document ID from @mention in text"""
        import re
        match = re.search(r'@(\S+)', text)
        return match.group(1) if match else ''

    def _is_path_context(self, text: str) -> bool:
        """Check if we're in a context that expects a path"""
        words = text.split()
        if not words:
            return False
        
        last_word = words[-1]
        
        # Context indicators that suggest a path is needed
        path_indicators = [
            'upload', 'process', 'from', 'to', 'in', 'at', 
            'directory', 'file', 'path', 'folder', 'load',
            'find', 'search', 'with'
        ]
        
        # Check if previous word suggests path
        if len(words) > 1:
            prev_word = words[-2].lower()
            if any(indicator in prev_word for indicator in path_indicators):
                return True
        
        # Check if current word looks like a path
        looks_like_path = (
            last_word.startswith('./') or 
            last_word.startswith('../') or
            last_word.startswith('/') or
            last_word.startswith('~') or
            '.' in last_word or
            '/' in last_word
        )
        
        return looks_like_path
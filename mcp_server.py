import os
import argparse  # Import the argparse library
from pathlib import Path
from dataclasses import field, Field
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from core.file_processor import FileProcessor, ProcessedContent
import json
from typing import Dict, List, Any, Optional

# --- Main Script Logic ---
mcp = FastMCP("DocumentMCP", log_level="ERROR")

docs = {}
# Global variable to store the working directory
working_directory = None
# File processor instance
file_processor = FileProcessor()
# Store processed content with metadata
processed_docs = {}  # doc_id -> ProcessedContent

#tool to read a doc
@mcp.tool(
    name="read_doc_contents",
    description="This tool reads the contents of the document and returns it as a string"
)
def read_doc_contents(
        doc_id: str= Field(description="Id of the document to read")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id:{doc_id} not found")
    return docs[doc_id]
#tool to edit a doc
@mcp.tool(
    name="edit_doc_contents",description="This tool edits the contents of the document by replacing a string in the documents with a new one."
)
def edit_doc_contents(
        doc_id: str=Field(description="Id of the document that will be edited "),
        old_str:str=Field(description="The Text to replace .Must match exactly ,including whitespace"),
        new_str:str=Field(description="The New Text to insert in place of the old text")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id:{doc_id} not found")
    docs[doc_id] = docs[doc_id].replace(old_str, new_str)

@mcp.tool(
    name="upload_document",
    description="Upload a document to the server's memory for analysis and manipulation"
)
def upload_document(
    filename: str = Field(description="Name of the file to upload"),
    content: str = Field(description="Content of the document to upload"),
    file_path: Optional[str] = Field(default=None, description="Path to the file for advanced processing")
):
    """Upload a document to the server's docs dictionary with advanced processing"""
    docs[filename] = content
    
    # If file_path is provided, process the file for metadata and chunks
    if file_path and os.path.exists(file_path):
        try:
            processed = file_processor.process_file(file_path)
            processed_docs[filename] = processed
            return f"Successfully uploaded document '{filename}' ({len(content)} characters) with metadata and {len(processed.chunks)} chunks"
        except Exception as e:
            return f"Successfully uploaded document '{filename}' ({len(content)} characters) but metadata processing failed: {str(e)}"
    else:
        # Create basic processed content for text-only uploads
        from core.file_processor import FileMetadata
        from datetime import datetime
        metadata = FileMetadata(
            filename=filename,
            file_path=filename,
            file_size=len(content),
            mime_type="text/plain",
            created_time=datetime.now(),
            modified_time=datetime.now(),
            file_type="text"
        )
        processed = ProcessedContent(content=content, metadata=metadata)
        processed_docs[filename] = processed
        return f"Successfully uploaded document '{filename}' ({len(content)} characters)"

# a resource to return all doc id's
@mcp.resource(
    "docs://documents",
    mime_type="application/json",
)
def list_docs() -> list[str]:
    return list(docs.keys())

# a resource to return the contents of a particular doc
@mcp.resource(
    "docs://document/{doc_id}",
    mime_type="text/plain",
)
def read_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id:{doc_id} not found")
    return docs[doc_id]


# New file operations for folder access
@mcp.tool(
    name="set_working_directory",
    description="Set the working directory for file operations. This allows the agent to work with any files in the specified folder."
)
def set_working_directory(
    directory_path: str = Field(description="Path to the directory to work with")
):
    global working_directory
    path = Path(directory_path)
    if not path.exists():
        raise ValueError(f"Directory '{directory_path}' does not exist")
    if not path.is_dir():
        raise ValueError(f"'{directory_path}' is not a directory")
    working_directory = path
    return f"Working directory set to: {working_directory}"

@mcp.tool(
    name="list_files",
    description="List all files in the working directory with their relative paths"
)
def list_files(
    pattern: str = Field(default="*", description="File pattern to match (e.g., '*.py', '*.md')")
):
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    files = []
    for file_path in working_directory.rglob(pattern):
        if file_path.is_file():
            relative_path = file_path.relative_to(working_directory)
            files.append(str(relative_path))
    
    return files

@mcp.tool(
    name="read_file",
    description="Read the contents of a file from the working directory"
)
def read_file(
    file_path: str = Field(description="Relative path to the file from the working directory")
):
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    full_path = working_directory / file_path
    if not full_path.exists():
        raise ValueError(f"File '{file_path}' does not exist in working directory")
    if not full_path.is_file():
        raise ValueError(f"'{file_path}' is not a file")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Error reading file '{file_path}': {e}")

@mcp.tool(
    name="write_file",
    description="Write content to a file in the working directory"
)
def write_file(
    file_path: str = Field(description="Relative path to the file from the working directory"),
    content: str = Field(description="Content to write to the file")
):
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    full_path = working_directory / file_path
    
    try:
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to '{file_path}'"
    except Exception as e:
        raise ValueError(f"Error writing to file '{file_path}': {e}")

@mcp.tool(
    name="get_file_info",
    description="Get information about a file (size, modification time, etc.)"
)
def get_file_info(
    file_path: str = Field(description="Relative path to the file from the working directory")
):
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    full_path = working_directory / file_path
    if not full_path.exists():
        raise ValueError(f"File '{file_path}' does not exist in working directory")
    
    stat = full_path.stat()
    return {
        "path": str(file_path),
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "is_file": full_path.is_file(),
        "is_directory": full_path.is_dir()
    }

@mcp.tool(
    name="search_in_files",
    description="Search for text patterns in files within the working directory"
)
def search_in_files(
    pattern: str = Field(description="Text pattern to search for"),
    file_pattern: str = Field(default="*", description="File pattern to search in (e.g., '*.py', '*.md')"),
    case_sensitive: bool = Field(default=False, description="Whether the search should be case sensitive")
):
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    results = []
    import re
    
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags)
    
    for file_path in working_directory.rglob(file_pattern):
        if file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = list(regex.finditer(content))
                    if matches:
                        relative_path = file_path.relative_to(working_directory)
                        results.append({
                            "file": str(relative_path),
                            "matches": len(matches),
                            "lines": [content[:match.start()].count('\n') + 1 for match in matches]
                        })
            except Exception as e:
                # Skip files that can't be read as text
                continue
    
    return results

@mcp.tool(
    name="get_document_metadata",
    description="Get detailed metadata about a document including file type, size, creation date, etc."
)
def get_document_metadata(
    doc_id: str = Field(description="ID of the document to get metadata for")
):
    """Get comprehensive metadata about a document"""
    if doc_id not in processed_docs:
        raise ValueError(f"Document with id '{doc_id}' not found")
    
    processed = processed_docs[doc_id]
    metadata = processed.metadata
    
    return {
        "filename": metadata.filename,
        "file_path": metadata.file_path,
        "file_size": metadata.file_size,
        "mime_type": metadata.mime_type,
        "file_type": metadata.file_type,
        "created_time": metadata.created_time.isoformat(),
        "modified_time": metadata.modified_time.isoformat(),
        "encoding": metadata.encoding,
        "page_count": metadata.page_count,
        "dimensions": metadata.dimensions,
        "language": metadata.language,
        "chunk_count": len(processed.chunks) if processed.chunks else 1,
        "content_length": len(processed.content)
    }

@mcp.tool(
    name="get_document_chunks",
    description="Get document content split into chunks for better processing"
)
def get_document_chunks(
    doc_id: str = Field(description="ID of the document to get chunks for"),
    chunk_index: Optional[int] = Field(default=None, description="Specific chunk index (0-based), or None for all chunks")
):
    """Get document chunks for processing large documents"""
    if doc_id not in processed_docs:
        raise ValueError(f"Document with id '{doc_id}' not found")
    
    processed = processed_docs[doc_id]
    chunks = processed.chunks or [processed.content]
    
    if chunk_index is not None:
        if 0 <= chunk_index < len(chunks):
            return {
                "doc_id": doc_id,
                "chunk_index": chunk_index,
                "total_chunks": len(chunks),
                "content": chunks[chunk_index]
            }
        else:
            raise ValueError(f"Chunk index {chunk_index} out of range. Document has {len(chunks)} chunks.")
    
    return {
        "doc_id": doc_id,
        "total_chunks": len(chunks),
        "chunks": chunks
    }

@mcp.tool(
    name="search_documents",
    description="Search across all uploaded documents for specific text patterns"
)
def search_documents(
    query: str = Field(description="Text to search for"),
    doc_ids: Optional[List[str]] = Field(default=None, description="Specific document IDs to search in, or None for all documents"),
    case_sensitive: bool = Field(default=False, description="Whether search should be case sensitive")
):
    """Search for text across documents"""
    import re
    
    if doc_ids is None:
        doc_ids = list(processed_docs.keys())
    
    results = []
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(query, flags)
    
    for doc_id in doc_ids:
        if doc_id not in processed_docs:
            continue
            
        processed = processed_docs[doc_id]
        content = processed.content
        
        matches = list(pattern.finditer(content))
        if matches:
            results.append({
                "doc_id": doc_id,
                "filename": processed.metadata.filename,
                "match_count": len(matches),
                "matches": [
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(),
                        "line": content[:match.start()].count('\n') + 1
                    }
                    for match in matches
                ]
            })
    
    return {
        "query": query,
        "total_matches": sum(r["match_count"] for r in results),
        "documents_found": len(results),
        "results": results
    }

@mcp.tool(
    name="get_supported_file_types",
    description="Get list of supported file types and their processing capabilities"
)
def get_supported_file_types():
    """Get information about supported file types"""
    return {
        "supported_extensions": file_processor.get_supported_extensions(),
        "processors_available": {
            "pdf": "PyPDF2" in globals(),
            "docx": "DocxDocument" in globals(),
            "ocr": "pytesseract" in globals(),
            "magic": "magic" in globals()
        }
    }

@mcp.tool(
    name="process_file_advanced",
    description="Process a file from the working directory with advanced metadata extraction"
)
def process_file_advanced(
    file_path: str = Field(description="Relative path to the file from the working directory"),
    chunk_size: int = Field(default=2000, description="Size of chunks to create for large files")
):
    """Process a file with advanced metadata extraction and chunking"""
    if working_directory is None:
        raise ValueError("No working directory set. Use set_working_directory first.")
    
    full_path = working_directory / file_path
    if not full_path.exists():
        raise ValueError(f"File '{file_path}' does not exist in working directory")
    
    try:
        processed = file_processor.process_file(str(full_path), chunk_size)
        processed_docs[file_path] = processed
        docs[file_path] = processed.content
        
        return {
            "filename": processed.metadata.filename,
            "file_type": processed.metadata.file_type,
            "file_size": processed.metadata.file_size,
            "chunk_count": len(processed.chunks),
            "content_length": len(processed.content),
            "message": f"Successfully processed '{file_path}' with {len(processed.chunks)} chunks"
        }
    except Exception as e:
        raise ValueError(f"Error processing file '{file_path}': {str(e)}")

# Enhanced prompt for document summarization
@mcp.prompt(
    name="summarize_document",
    description="Generate a comprehensive summary of a document with key insights and structure"
)
def summarize_document(
    doc_id: str = Field(description="ID of the document to summarize"),
    summary_type: str = Field(default="comprehensive", description="Type of summary: 'brief', 'comprehensive', 'detailed', 'outline'")
) -> list[base.Message]:
    """Generate a summary of the specified document"""
    
    if doc_id not in processed_docs:
        return [base.UserMessage(f"Document '{doc_id}' not found. Available documents: {list(processed_docs.keys())}")]
    
    processed = processed_docs[doc_id]
    metadata = processed.metadata
    
    prompt = f"""Please analyze and summarize the following document:

DOCUMENT METADATA:
- Filename: {metadata.filename}
- File Type: {metadata.file_type}
- File Size: {metadata.file_size} bytes
- Created: {metadata.created_time}
- Modified: {metadata.modified_time}
- MIME Type: {metadata.mime_type}
- Chunks: {len(processed.chunks) if processed.chunks else 1}

SUMMARY TYPE REQUESTED: {summary_type}

DOCUMENT CONTENT:
{processed.content}

Please provide a {summary_type} summary that includes:
1. Main topics and themes
2. Key points and insights
3. Document structure (if applicable)
4. Important details or data
5. Conclusions or recommendations (if any)

Format the summary in markdown with clear headings and bullet points."""
    
    return [base.UserMessage(prompt)]

# Enhanced prompt for document formatting
@mcp.prompt(
    name="format_document",
    description="Reformat a document with improved structure, headings, and markdown formatting"
)
def format_document(
    doc_id: str = Field(description="ID of the document to format"),
    format_style: str = Field(default="markdown", description="Format style: 'markdown', 'structured', 'outline'")
) -> list[base.Message]:
    """Reformat a document with better structure and formatting"""
    
    if doc_id not in processed_docs:
        return [base.UserMessage(f"Document '{doc_id}' not found. Available documents: {list(processed_docs.keys())}")]
    
    processed = processed_docs[doc_id]
    
    prompt = f"""Please reformat the following document with improved structure and {format_style} formatting:

DOCUMENT TO FORMAT: {doc_id}
CURRENT CONTENT:
{processed.content}

Please:
1. Add appropriate headings and subheadings
2. Organize content into logical sections
3. Use bullet points, numbered lists, and tables where appropriate
4. Improve readability and flow
5. Maintain all important information
6. Use proper {format_style} formatting

After formatting, use the edit_doc_contents tool to update the document with the improved version."""
    
    return [base.UserMessage(prompt)]


# New MCP prompts for Option 2: Pure MCP approach
@mcp.prompt(
    name="find_and_load_project",
    description="Find a project by marker file and load all documents from it"
)
def find_and_load_project(
    marker_filename: str = Field(description="Marker file to search for (e.g., 'pyproject.toml', 'package.json')")
) -> list[base.Message]:
    prompt = f"""I need you to find a project directory containing the marker file '{marker_filename}' and load all supported documents from it.

Please:
1. Search for a directory containing '{marker_filename}' starting from current directory
2. Use set_working_directory tool to set that directory as working directory  
3. Use list_files tool to find all supported documents (.txt, .md, .pdf, .docx)
4. Use process_file_advanced tool to load each document with metadata and chunking
5. Confirm when all documents are loaded

Marker file to find: '{marker_filename}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="upload_directory",
    description="Upload all documents from a specified directory"
)
def upload_directory(
    directory_path: str = Field(description="Path to the directory to upload documents from")
) -> list[base.Message]:
    prompt = f"""I need you to upload all supported documents from the directory '{directory_path}'.

Please:
1. Use set_working_directory to set the working directory to '{directory_path}'
2. Use list_files to find all supported documents (.txt, .md, .pdf, .docx)
3. Use process_file_advanced to load each document with metadata and chunking
4. Show progress and confirm when all documents are loaded

Directory path: '{directory_path}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="process_single_file",
    description="Process a single file with advanced metadata extraction"
)
def process_single_file(
    file_path: str = Field(description="Path to the file to process")
) -> list[base.Message]:
    prompt = f"""I need you to process the file '{file_path}' with advanced metadata extraction.

Please:
1. Use process_file_advanced tool to process '{file_path}' with chunk_size=2000
2. Show the processing results including file type, size, and chunk count
3. Confirm when processing is complete

File to process: '{file_path}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="show_document_metadata",
    description="Show detailed metadata for a document"
)
def show_document_metadata(
    doc_id: str = Field(description="ID of the document to show metadata for")
) -> list[base.Message]:
    prompt = f"""Please show detailed metadata for the document '{doc_id}'.

Use get_document_metadata tool and display:
- Filename, file type, file size
- Creation and modification times  
- MIME type, encoding, chunk count
- Any special metadata (page count, dimensions, language)

Format the metadata clearly and comprehensively.

Document ID: '{doc_id}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="search_all_documents",
    description="Search across all documents for specific text patterns"
)
def search_all_documents(
    query: str = Field(description="Text to search for across all documents")
) -> list[base.Message]:
    prompt = f"""Please search for '{query}' across all loaded documents.

Use search_documents tool and display:
- Total matches found
- Documents that contain matches
- Sample matches with line numbers
- Clear formatting of results

Search query: '{query}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="show_document_chunks",
    description="Show document content split into chunks"
)
def show_document_chunks(
    doc_id: str = Field(description="ID of the document to show chunks for")
) -> list[base.Message]:
    prompt = f"""Please show the chunks for document '{doc_id}'.

Use get_document_chunks tool and display:
- Total number of chunks
- Each chunk with preview (truncate if too long)
- Clear chunk numbering and formatting

Document ID: '{doc_id}'"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="show_supported_types",
    description="Show supported file types and processing capabilities"
)
def show_supported_types() -> list[base.Message]:
    prompt = """Please show the supported file types and processing capabilities.

Use get_supported_file_types tool and display:
- All supported file extensions
- Available processors and their status
- Processing capabilities for each file type
- Clear formatting of the information"""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="show_agent_status",
    description="Show current agent status and loaded documents"
)
def show_agent_status() -> list[base.Message]:
    prompt = """Please show the current status of the CogniDocs agent.

Display a comprehensive status report including:
1. Use the docs resource to show loaded documents
2. Use get_supported_file_types to show capabilities  
3. Show available documents with @mention format
4. Show MCP server connection status
5. Format as a clear status dashboard

Provide a complete overview of the current system state."""
    
    return [base.UserMessage(prompt)]

@mcp.prompt(
    name="quit_application",
    description="Exit the application gracefully"
)
def quit_application() -> list[base.Message]:
    prompt = """The user wants to quit the application. 

Please:
1. Acknowledge the request
2. Provide a friendly goodbye message
3. Confirm that the session is ending

This will end the current CogniDocs session."""
    
    return [base.UserMessage(prompt)]


if __name__ == "__main__":
    # The server is now simpler. It just starts and waits for API calls.
    mcp.run(transport="stdio") # Or FastAPI later
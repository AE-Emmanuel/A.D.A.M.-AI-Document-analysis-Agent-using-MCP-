# A.D.A.M. - AI Based Document Analysis Agent Using MCP 
*(Disclaimer: A.D.A.M. is a playful acronym 😄)*

A.D.A.M. is an intelligent document assistant that combines the power of Any LLM with the Model Control Protocol (MCP) to provide natural language document analysis and management. Built with Python, it offers a sophisticated command-line interface for uploading, processing, and chatting about your documents using advanced AI capabilities.

## Key Features
- 🎯 **Natural Language MCP**: Revolutionary approach - no need to learn tool names or syntax, just speak naturally and A.D.A.M. automatically uses the right MCP tools and prompts
- 📄 **Multi-Format Support**: Process PDFs, Word docs, text files, images, and more  
- 📊 **Advanced Metadata**: Extract detailed file information and structure
- 🧠 **MCP Architecture**: Extensible tool-based AI agent system
- 💬 **Document Mentions**: Reference specific files using `@filename` syntax

## Prerequisites
- Python 3.9 or higher
- OpenRouter API Key or Any LLMs API 

### Supported File Types
| Category | Extensions | Features |
|----------|------------|----------|
| **Text Files** | `.txt`, `.md`, `.py`, `.js`, `.html`, `.css` | Automatic encoding detection, intelligent chunking |
| **Documents** | `.pdf`, `.docx` | Text extraction, metadata extraction (pages, author, etc.) |
| **Images** | `.png`, `.jpg`, `.jpeg`| OCR text extraction, dimension analysis |

### Advanced Features
- **Metadata Extraction**: File size, type, creation/modification dates, encoding, dimensions
- **Intelligent Chunking**: Splits large files into manageable pieces for processing
- **OCR Processing**: Extract text from images using Tesseract (when available)
- **Cross-Document Search**: Find patterns across your entire document collection
- **Document Analysis**: Structure analysis, content summaries, and insights


### Project Structure
```
adam/
├── main.py              # Entry point
├── mcp_server.py        # MCP agent server with tools
├── mcp_client.py        # MCP client for server communication
├── core/
│   ├── cli.py          # Command-line interface
│   ├── cli_chat.py     # Agent loop and chat logic
│   ├── claude.py       # Claude API integration
│   ├── chat.py         # Base chat interface
│   └── file_processor.py # Advanced file processing
├── pyproject.toml      # Project configuration
└── README.md
```

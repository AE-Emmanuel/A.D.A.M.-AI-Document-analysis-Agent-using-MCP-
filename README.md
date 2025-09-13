# MCP Chat 🚀

MCP Chat is a command-line interface (CLI) application that enables interactive chatting with AI models via the Anthropic API. It supports document retrieval, command-based prompts, and extensible tool integrations through the MCP (Model Control Protocol) architecture.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
- [Commands](#commands)
- [Document Retrieval](#document-retrieval)
- [Enhanced File Processing](#enhanced-file-processing)
- [File Operations](#file-operations)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Prerequisites
- Python 3.9 or higher
- Anthropic API Key (obtain from [Anthropic](https://console.anthropic.com/))

## Setup

### Step 1: Configure Environment Variables
1. Create or edit the `.env` file in the project root:
   ```
   ANTHROPIC_API_KEY=your_api_key_here  # Replace with your Anthropic API secret key
   ```

### Step 2: Install Dependencies

#### Option 1: Using uv (Recommended for Speed)
[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

1. Install uv (if not already installed):
   ```bash
   pip install uv
   ```

2. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install core dependencies:
   ```bash
   uv pip install -e .
   ```

4. Install additional dependencies for advanced file processing:
   ```bash
   # For PDF processing
   uv pip install PyPDF2

   # For DOCX processing
   uv pip install python-docx

   # For image OCR processing
   uv pip install Pillow pytesseract

   # For file type detection
   uv pip install python-magic

   # For encoding detection
   uv pip install chardet
   ```

5. Run the application:
   ```bash
   uv run main.py
   ```

6. Test enhanced features:
   ```bash
   uv run test_enhanced_features.py
   ```

#### Option 2: Standard Setup (Without uv)
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install anthropic python-dotenv prompt-toolkit "mcp[cli]==1.8.0"
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Basic Interaction
Type your message and press Enter to chat with the AI model. Example:
```
> Hello, how are you?
```

### Auto Folder Detection
The agent automatically scans for new project folders every 15 seconds:
- **Smart Detection**: Identifies folders by markers like `package.json`, `pyproject.toml`, etc.
- **User Confirmation**: Prompts before adding discovered folders.
- **Seamless Integration**: Loads documents and sets the working directory automatically.

## Commands
Use these slash commands for advanced functionality:

### Document Management
- `/find <filename>` - Find and load a project by marker file.
- `/upload <directory>` - Upload all documents from a directory.
- `/process <file>` - Process a single file with advanced metadata extraction.
- `/status` - Display current agent status.

### Document Analysis
- `/metadata <doc_id>` - Show detailed metadata (size, type, dates, etc.) for a document.
- `/search <query>` - Search across all documents for text patterns.
- `/chunks <doc_id>` - View document content split into chunks.
- `/types` - List supported file types and processing capabilities.

### System
- `/quit` - Exit the application.

## Document Retrieval
Reference documents in queries using `@<doc_id>` to include their content:
```
> Tell me about @deposition.md
```

## Enhanced File Processing
Supports advanced metadata extraction, chunking, and OCR.

### Supported File Types
| Category | Extensions | Features |
|----------|------------|----------|
| **Text Files** | `.txt`, `.md`, `.py`, `.js`, `.html`, `.css`, `.json`, `.xml`, `.csv`, `.log` | Automatic encoding detection, chunking for large files. |
| **Documents** | `.pdf`, `.docx`, `.doc` | Text extraction, metadata (e.g., page count, author). |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff` | OCR for text extraction, dimension analysis. |

### Advanced Features
- **Metadata Extraction**: Includes file size, type, creation/modification dates, encoding, and dimensions.
- **Document Chunking**: Splits large files into 2000-character chunks for efficient processing.
- **OCR Processing**: Extracts text from images using Tesseract.
- **Cross-Document Search**: Query patterns across multiple documents.
- **Document Analysis**: Inspect structure, content summaries, and more.

## File Operations
Interact with files in your workspace via natural language:
- "List all Python files in the directory."
- "Read the main.py file and explain what it does."
- "Search for 'import' in all Python files."
- "Write a new file called test.py with some code."
- "Summarize the @report.pdf document."
- "Find all mentions of 'API' across all documents."

## Development

### Adding New Documents
Edit `mcp_server.py` to add entries to the `docs` dictionary.

### Implementing MCP Features
1. Complete TODOs in `mcp_server.py`.
2. Implement missing functionality in `mcp_client.py`.

### Linting and Type Checking
Currently, no linting or type checks are implemented. Consider adding:
```bash
pip install ruff mypy
ruff check .
mypy .
```

## Troubleshooting
- **API Key Issues**: Ensure `.env` is loaded correctly (check `python-dotenv` installation).
- **Dependency Errors**: Verify virtual environment activation and run `pip list` to confirm packages.
- **File Not Found**: Use `/status` to check working directory; set it with `set_working_directory <path>`.
- **OCR Fails**: Install Tesseract binary (e.g., via Homebrew: `brew install tesseract` on macOS).
- **Large Files**: If processing hangs, increase chunk size or use `/chunks` manually.

For more help, run `/status` in the app or describe the issue here!
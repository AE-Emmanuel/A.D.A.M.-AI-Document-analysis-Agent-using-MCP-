"""
Advanced file processing module for the MCP agent.
Supports multiple file types with metadata extraction and content processing.
"""

import os
import mimetypes
import chardet
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


@dataclass
class FileMetadata:
    """Metadata for uploaded files"""
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    created_time: datetime
    modified_time: datetime
    file_type: str
    encoding: Optional[str] = None
    page_count: Optional[int] = None
    dimensions: Optional[Tuple[int, int]] = None
    language: Optional[str] = None


@dataclass
class ProcessedContent:
    """Processed file content with metadata"""
    content: str
    metadata: FileMetadata
    chunks: List[str] = None
    summary: Optional[str] = None


class FileProcessor:
    """Advanced file processor supporting multiple file types"""
    
    def __init__(self):
        self.supported_extensions = {
            '.txt': self._process_text,
            '.md': self._process_text,

            '.py': self._process_text,
            '.js': self._process_text,
            '.html': self._process_text,
            '.css': self._process_text,

            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.doc': self._process_docx,

            '.png': self._process_image,
            '.jpg': self._process_image,
            '.jpeg': self._process_image
        }
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file type is supported"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions
    
    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """Extract comprehensive file metadata"""
        path = Path(file_path)
        stat = path.stat()
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type and MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
            except:
                mime_type = "application/octet-stream"
        elif not mime_type:
            mime_type = "application/octet-stream"
        
        # Determine file type
        ext = path.suffix.lower()
        if ext in ['.txt', '.md', '.py', '.js', '.html', '.css']:
            file_type = 'text'
        elif ext in ['.pdf']:
            file_type = 'pdf'
        elif ext in ['.docx', '.doc']:
            file_type = 'docx'
        elif ext in ['.png', '.jpg', '.jpeg']:
            file_type = 'image'
        else:
            file_type = 'binary'
        
        return FileMetadata(
            filename=path.name,
            file_path=str(file_path),
            file_size=stat.st_size,
            mime_type=mime_type,
            created_time=datetime.fromtimestamp(stat.st_ctime),
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            file_type=file_type
        )
    
    def process_file(self, file_path: str, chunk_size: int = 2000) -> ProcessedContent:
        """Process a file and extract content with metadata"""
        if not self.is_supported(file_path):
            raise ValueError(f"Unsupported file type: {Path(file_path).suffix}")
        
        metadata = self.get_file_metadata(file_path)
        processor = self.supported_extensions[Path(file_path).suffix.lower()]
        
        try:
            content = processor(file_path)
            metadata.encoding = self._detect_encoding(file_path)
            
            # Create chunks for large files
            chunks = self._create_chunks(content, chunk_size)
            
            return ProcessedContent(
                content=content,
                metadata=metadata,
                chunks=chunks
            )
        except Exception as e:
            raise ValueError(f"Error processing file {file_path}: {str(e)}")
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8')
        except:
            return 'utf-8'
    
    def _process_text(self, file_path: str) -> str:
        """Process text files"""
        encoding = self._detect_encoding(file_path)
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    
    def _process_pdf(self, file_path: str) -> str:
        """Process PDF files"""
        if not PDF_AVAILABLE:
            return f"PDF processing not available. Install PyPDF2 to process PDF files."
        
        try:
            content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content.append(page.extract_text())
            return '\n'.join(content)
        except Exception as e:
            return f"Error processing PDF: {str(e)}"
    
    def _process_docx(self, file_path: str) -> str:
        """Process DOCX files"""
        if not DOCX_AVAILABLE:
            return f"DOCX processing not available. Install python-docx to process DOCX files."
        
        try:
            doc = DocxDocument(file_path)
            content = []
            for paragraph in doc.paragraphs:
                content.append(paragraph.text)
            return '\n'.join(content)
        except Exception as e:
            return f"Error processing DOCX: {str(e)}"
    
    def _process_image(self, file_path: str) -> str:
        """Process image files using OCR"""
        if not OCR_AVAILABLE:
            return f"Image OCR not available. Install Pillow and pytesseract to process images."
        
        try:
            image = Image.open(file_path)
            # Get image dimensions
            width, height = image.size
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            # Add image metadata to the content
            metadata_text = f"[IMAGE METADATA]\nDimensions: {width}x{height}\nFile: {Path(file_path).name}\n\n"
            return metadata_text + text
        except Exception as e:
            return f"Error processing image: {str(e)}"
    
    def _create_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Split content into chunks for better processing"""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return list(self.supported_extensions.keys())
    
    def get_file_type_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed information about a file type"""
        ext = Path(file_path).suffix.lower()
        metadata = self.get_file_metadata(file_path)
        
        return {
            'extension': ext,
            'file_type': metadata.file_type,
            'mime_type': metadata.mime_type,
            'supported': ext in self.supported_extensions,
            'processor_available': self._is_processor_available(ext)
        }
    
    def _is_processor_available(self, ext: str) -> bool:
        """Check if processor for file type is available"""
        if ext == '.pdf':
            return PDF_AVAILABLE
        elif ext in ['.docx', '.doc']:
            return DOCX_AVAILABLE
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return OCR_AVAILABLE
        else:
            return True

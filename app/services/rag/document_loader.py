"""
Document Loader for RAG
Supports PDF, TXT, MD, and DOCX file formats
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import mimetypes

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Load documents from various formats (PDF, TXT, MD, DOCX)
    """

    SUPPORTED_FORMATS = {".pdf", ".txt", ".md", ".docx"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if file format is supported"""
        path = Path(file_path)
        return path.suffix.lower() in DocumentLoader.SUPPORTED_FORMATS

    @staticmethod
    async def load_document(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Load document and return (filename, [pages/sections])

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (filename, list of page/section dicts with content, source, page)
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > DocumentLoader.MAX_FILE_SIZE:
            raise ValueError(
                f"File too large: {file_size} bytes (max: {DocumentLoader.MAX_FILE_SIZE})"
            )

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return await DocumentLoader.load_pdf(file_path)
        elif suffix == ".txt":
            return await DocumentLoader.load_txt(file_path)
        elif suffix == ".md":
            return await DocumentLoader.load_md(file_path)
        elif suffix == ".docx":
            return await DocumentLoader.load_docx(file_path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")

    @staticmethod
    async def load_pdf(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Load PDF document using PyMuPDF"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            pages = []

            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    pages.append(
                        {
                            "content": text,
                            "source": f"{Path(file_path).name}:page_{page_num}",
                            "page": page_num,
                            "type": "pdf",
                        }
                    )

            doc.close()
            logger.info(f"Loaded PDF: {file_path} ({len(pages)} pages)")
            return Path(file_path).name, pages

        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) is required for PDF support. Install with: pip install PyMuPDF"
            )
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise

    @staticmethod
    async def load_txt(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Load TXT document"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return Path(file_path).name, [
                {
                    "content": content,
                    "source": Path(file_path).name,
                    "page": 1,
                    "type": "txt",
                }
            ]
        except Exception as e:
            logger.error(f"Error loading TXT: {e}")
            raise

    @staticmethod
    async def load_md(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Load Markdown document"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return Path(file_path).name, [
                {
                    "content": content,
                    "source": Path(file_path).name,
                    "page": 1,
                    "type": "md",
                }
            ]
        except Exception as e:
            logger.error(f"Error loading MD: {e}")
            raise

    @staticmethod
    async def load_docx(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Load DOCX document"""
        try:
            from docx import Document

            doc = Document(file_path)
            content = "\n".join(
                [para.text for para in doc.paragraphs if para.text.strip()]
            )

            return Path(file_path).name, [
                {
                    "content": content,
                    "source": Path(file_path).name,
                    "page": 1,
                    "type": "docx",
                }
            ]
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX support. Install with: pip install python-docx"
            )
        except Exception as e:
            logger.error(f"Error loading DOCX: {e}")
            raise

    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Get file information without loading content"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return {
            "filename": path.name,
            "size": path.stat().st_size,
            "extension": path.suffix.lower(),
            "is_supported": DocumentLoader.is_supported(file_path),
            "mime_type": mimetypes.guess_type(str(path))[0]
            or "application/octet-stream",
        }

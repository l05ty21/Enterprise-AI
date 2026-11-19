"""文档解析与切片。

支持的格式：txt / md / csv / pdf / docx。
切片策略：先按空行分段，再把段落拼到接近上限；单段超长则按字符硬切并保留重叠，
保证跨切片的句子语义不会完全断掉。
"""

from __future__ import annotations

import io
import re

from app.core.exceptions import BadRequestError

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx"}


def extension_of(filename: str) -> str:
    name = (filename or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""


def extract_text(filename: str, data: bytes) -> str:
    """把上传的文件转成纯文本。"""
    if len(data) > MAX_FILE_BYTES:
        raise BadRequestError("文件超过 20 MB 限制")

    ext = extension_of(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise BadRequestError(f"暂不支持 {ext or '该'} 格式，请上传 {allowed}")

    if ext in {".txt", ".md", ".csv"}:
        return _decode_text(data)
    if ext == ".pdf":
        return _extract_pdf(data)
    return _extract_docx(data)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BadRequestError("无法识别文件编码，请另存为 UTF-8 后重试")


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出明确提示
        raise BadRequestError("缺少 pypdf 依赖，无法解析 PDF") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except Exception as exc:
        raise BadRequestError(f"PDF 解析失败：{exc}") from exc


def _extract_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise BadRequestError("缺少 python-docx 依赖，无法解析 Word") from exc

    try:
        document = docx.Document(io.BytesIO(data))
        parts = [paragraph.text.strip() for paragraph in document.paragraphs]
        # 表格内容也收进来，否则制度类文档会丢很多信息
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n\n".join(part for part in parts if part)
    except Exception as exc:
        raise BadRequestError(f"Word 解析失败：{exc}") from exc


def chunk_text(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """按段落优先、超长硬切的策略切片。"""
    cleaned = re.sub(r"\r\n?", "\n", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        return []

    paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(paragraph) <= size:
            candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
            if len(candidate) <= size:
                buffer = candidate
                continue
            chunks.append(buffer)
            buffer = paragraph
            continue

        # 单段就超过上限：先把缓冲冲掉，再按固定窗口硬切
        if buffer:
            chunks.append(buffer)
            buffer = ""
        start = 0
        while start < len(paragraph):
            chunks.append(paragraph[start : start + size])
            start += max(size - overlap, 1)

    if buffer:
        chunks.append(buffer)

    return [chunk for chunk in chunks if chunk.strip()]

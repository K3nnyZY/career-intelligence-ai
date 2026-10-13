"""Bounded, ephemeral document parsing. No filenames or file contents are logged."""
import io
import logging
import multiprocessing
import sys
import threading
import zipfile

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 40
MAX_TEXT = 100_000
MAX_UNCOMPRESSED = 20 * 1024 * 1024
PARSE_TIMEOUT = 12
PARSER_SLOTS = threading.BoundedSemaphore(2)
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentError(ValueError):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.status = code, status


def _parse_pdf(content):
    from pypdf import PdfReader
    if not content.startswith(b"%PDF-"):
        raise DocumentError("invalid_format", "El archivo no tiene una cabecera PDF válida.")
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        raise DocumentError("encrypted_pdf", "Usa un PDF sin contraseña.")
    if len(reader.pages) > MAX_PAGES:
        raise DocumentError("too_many_pages", f"El límite es {MAX_PAGES} páginas.")
    parts, blank_pages, length = [], 0, 0
    for page in reader.pages:
        text = page.extract_text() or ""
        blank_pages += not bool(text.strip())
        length += len(text) + 1
        if length > MAX_TEXT:
            raise DocumentError("text_too_large", "El texto extraído supera el límite permitido.")
        parts.append(text)
    warnings = ["Hay páginas sin texto extraíble. Revisa que no falte experiencia; este MVP no incluye OCR."] if blank_pages else []
    return "\n".join(parts), warnings


def _parse_docx(content):
    from defusedxml.ElementTree import fromstring
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(item.file_size for item in entries) > MAX_UNCOMPRESSED:
            raise DocumentError("archive_too_large", "El DOCX expandido supera el límite permitido.")
        names = [item.filename for item in entries]
        if len(names) != len(set(names)):
            raise DocumentError("invalid_docx", "El DOCX contiene entradas duplicadas.")
        if "word/document.xml" not in names or "[Content_Types].xml" not in names:
            raise DocumentError("invalid_format", "El archivo no es un DOCX válido.")
        if any("vbaProject" in name for name in names):
            raise DocumentError("unsupported_macros", "No se admiten documentos con macros.")
        parts = []
        # Read body (including tables), headers and footers; never external relationships.
        relevant = [name for name in names if name == "word/document.xml" or
                    (name.startswith(("word/header", "word/footer")) and name.endswith(".xml"))]
        for name in sorted(relevant):
            root = fromstring(archive.read(name))
            for paragraph in root.iter(WORD_NS + "p"):
                tokens = []
                for node in paragraph.iter():
                    if node.tag == WORD_NS + "t":
                        tokens.append(node.text or "")
                    elif node.tag == WORD_NS + "tab":
                        tokens.append("\t")
                    elif node.tag in (WORD_NS + "br", WORD_NS + "cr"):
                        tokens.append("\n")
                parts.append("".join(tokens))
        return "\n".join(parts), ["Revisa el orden del texto: tablas, encabezados y columnas pueden alterar la lectura."]


def _worker(connection, content, document_format):
    # Silence parser messages that could contain document text.
    logging.disable(logging.CRITICAL)
    try:
        if sys.platform.startswith("linux"):
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024,) * 2)
        text, warnings = _parse_pdf(content) if document_format == "pdf" else _parse_docx(content)
        if not text.strip():
            raise DocumentError("no_text", "No se pudo leer texto. Si el CV es escaneado, conviértelo con OCR local o pega el texto manualmente.")
        if len(text) > MAX_TEXT:
            raise DocumentError("text_too_large", "El texto extraído supera el límite permitido.")
        connection.send({"text": text, "warnings": warnings, "format": document_format})
    except DocumentError as exc:
        connection.send({"error": exc.code, "message": str(exc), "status": exc.status})
    except Exception:
        connection.send({"error": "unreadable_document", "message": "No se pudo leer el documento. Comprueba que no esté dañado o pega el texto manualmente.", "status": 422})
    finally:
        connection.close()


def extract_document(content, document_format):
    if document_format not in {"pdf", "docx"}:
        raise DocumentError("unsupported_format", "Solo se admiten PDF y DOCX.", 415)
    if not content or len(content) > MAX_FILE_BYTES:
        raise DocumentError("invalid_size", "El archivo debe contener entre 1 byte y 5 MiB.", 413)
    if not PARSER_SLOTS.acquire(blocking=False):
        raise DocumentError("parser_busy", "El lector está ocupado. Inténtalo de nuevo.", 503)
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(sender, content, document_format), daemon=True)
    try:
        process.start()
        sender.close()
        if not receiver.poll(PARSE_TIMEOUT):
            raise DocumentError("parse_timeout", "El documento excedió el tiempo de lectura permitido.")
        try:
            result = receiver.recv()
        except EOFError:
            raise DocumentError("parser_failed", "El lector excedió sus recursos o no pudo leer el archivo.") from None
        if "error" in result:
            raise DocumentError(result["error"], result["message"], result["status"])
        return result
    finally:
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()
        receiver.close()
        sender.close()
        PARSER_SLOTS.release()

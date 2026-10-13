import unittest
from unittest.mock import Mock, patch

from career_ai.documents import DocumentError, MAX_FILE_BYTES, MAX_UNCOMPRESSED, PARSER_SLOTS, extract_document
from document_fixtures import docx_bytes, pdf_bytes


class DocumentTests(unittest.TestCase):
    def assert_error(self, content, document_format, code):
        with self.assertRaises(DocumentError) as error:
            extract_document(content, document_format)
        self.assertEqual(error.exception.code, code)

    def test_pdf_text_and_docx_tables(self):
        self.assertIn("SQL", extract_document(pdf_bytes(), "pdf")["text"])
        self.assertEqual(extract_document(docx_bytes(), "docx")["text"], "Built SQL pipelines\nPython")

    def test_blank_scanned_encrypted_and_page_limit(self):
        self.assert_error(pdf_bytes(text=None), "pdf", "no_text")
        self.assert_error(pdf_bytes(encrypted=True), "pdf", "encrypted_pdf")
        self.assert_error(pdf_bytes(text=None, pages=41), "pdf", "too_many_pages")

    def test_invalid_format_and_upload_size(self):
        self.assert_error(b"bad file", "pdf", "invalid_format")
        self.assert_error(b"bad file", "docx", "unreadable_document")
        self.assert_error(b"text", "txt", "unsupported_format")
        self.assert_error(b"", "pdf", "invalid_size")
        self.assert_error(b"x" * (MAX_FILE_BYTES + 1), "pdf", "invalid_size")

    def test_zip_expansion_and_xml_entities_are_rejected(self):
        self.assert_error(docx_bytes(extra=("word/media/large", b"a" * MAX_UNCOMPRESSED)), "docx", "archive_too_large")
        xml = '<!DOCTYPE root [<!ENTITY secret SYSTEM "file:///etc/passwd">]><root>&secret;</root>'
        self.assert_error(docx_bytes(xml=xml), "docx", "unreadable_document")
        self.assert_error(docx_bytes(extra=("word/vbaProject.bin", b"macro")), "docx", "unsupported_macros")

    def test_concurrency_limit(self):
        PARSER_SLOTS.acquire()
        PARSER_SLOTS.acquire()
        try:
            self.assert_error(b"pdf", "pdf", "parser_busy")
        finally:
            PARSER_SLOTS.release()
            PARSER_SLOTS.release()

    def test_timeout_kills_worker_and_releases_slot(self):
        receiver, sender, process = Mock(), Mock(), Mock()
        receiver.poll.return_value = False
        process.pid = 123
        process.is_alive.side_effect = [True, False]
        context = Mock()
        context.Pipe.return_value = receiver, sender
        context.Process.return_value = process
        with patch("career_ai.documents.multiprocessing.get_context", return_value=context):
            self.assert_error(b"pdf", "pdf", "parse_timeout")
        process.terminate.assert_called_once()
        receiver.close.assert_called_once()
        self.assertTrue(PARSER_SLOTS.acquire(blocking=False))
        PARSER_SLOTS.release()

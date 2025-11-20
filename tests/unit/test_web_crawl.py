"""Unit tests for the web_crawl tool."""

import pytest
from unittest.mock import patch, Mock
from bs4 import BeautifulSoup
from luminamind.py_tools.web_crawl import web_crawl

class TestWebCrawl:
    """Test cases for the web_crawl tool."""

    @patch('luminamind.py_tools.web_crawl.requests.get')
    def test_web_crawl_success(self, mock_get):
        """Test successful web crawling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Content</h1>
                <p>This is a test paragraph with some content.</p>
                <script>var x = 1;</script>
                <style>body { color: red; }</style>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        result = web_crawl.invoke({"url": "https://example.com"})
        
        assert result["error"] is False
        assert result["url"] == "https://example.com"
        assert "Test Content" in result["excerpt"]
        assert "This is a test paragraph" in result["excerpt"]
        assert "var x = 1;" not in result["excerpt"]  # Should be stripped
        assert "body { color: red; }" not in result["excerpt"]  # Should be stripped

    @patch('luminamind.py_tools.web_crawl.requests.get')
    def test_web_crawl_with_max_chars(self, mock_get):
        """Test web crawling with character limit."""
        long_text = "This is a very long text. " * 100
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = f"<html><body>{long_text}</body></html>"
        mock_get.return_value = mock_response
        
        result = web_crawl.invoke({"url": "https://example.com", "max_chars": 100})
        
        assert result["error"] is False
        assert len(result["excerpt"]) <= 100
        assert result["content_length"] == len(long_text.strip())

    @patch('luminamind.py_tools.web_crawl.requests.get')
    def test_web_crawl_http_error(self, mock_get):
        """Test web crawling with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response
        
        import requests
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
        
        result = web_crawl.invoke({"url": "https://example.com"})
        
        assert result["error"] is True
        assert "HTTP 404" in result["message"]

    @patch('luminamind.py_tools.web_crawl.requests.get')
    def test_web_crawl_request_exception(self, mock_get):
        """Test web crawling with request exception."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = web_crawl.invoke({"url": "https://example.com"})
        
        assert result["error"] is True
        assert "Connection error" in result["message"]

    def test_extract_text_function(self):
        """Test the internal _extract_text function."""
        from luminamind.py_tools.web_crawl import _extract_text
        
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Content</h1>
                <p>This is a test paragraph.</p>
                <script>var x = 1;</script>
                <style>body { color: red; }</style>
            </body>
        </html>
        """
        
        text = _extract_text(html)
        
        assert "Test Content" in text
        assert "This is a test paragraph." in text
        assert "var x = 1;" not in text
        assert "body { color: red; }" not in text

    def test_extract_text_with_special_characters(self):
        """Test text extraction with special characters."""
        from luminamind.py_tools.web_crawl import _extract_text
        
        html = """
        <html>
            <body>
                <p>Special characters: &amp; &lt; &gt; &quot;</p>
                <p>New lines and tabs should be handled properly</p>
            </body>
        </html>
        """
        
        text = _extract_text(html)
        
        assert "Special characters: & < > \"" in text
        assert "New lines and tabs should be handled properly" in text

    def test_extract_text_empty_html(self):
        """Test text extraction with empty HTML."""
        from luminamind.py_tools.web_crawl import _extract_text
        
        html = "<html></html>"
        text = _extract_text(html)
        
        assert text == ""

    def test_extract_text_minimal_html(self):
        """Test text extraction with minimal HTML."""
        from luminamind.py_tools.web_crawl import _extract_text
        
        html = "<html><body>Just text</body></html>"
        text = _extract_text(html)
        
        assert text == "Just text"

    @patch('luminamind.py_tools.web_crawl.requests.get')
    def test_web_crawl_redirect_handling(self, mock_get):
        """Test web crawling with redirect."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Redirected content</body></html>"
        mock_response.url = "https://example.com/redirected"
        mock_get.return_value = mock_response
        
        result = web_crawl.invoke({"url": "https://example.com/original"})
        
        assert result["error"] is False
        assert result["url"] == "https://example.com/original" # The tool returns the requested URL, not the final one
        assert "Redirected content" in result["excerpt"]

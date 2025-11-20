"""Unit tests for the web_search tool."""

import pytest
from unittest.mock import patch, Mock
from luminamind.py_tools.web_search import web_search, _search_google_cse, _search_serper, _search_ollama

class TestWebSearch:
    """Test cases for the web_search tool."""

    @patch('luminamind.py_tools.web_search._search_google_cse')
    def test_web_search_success_google_cse(self, mock_google_search):
        """Test successful web search using Google CSE."""
        mock_google_search.return_value = {
            "error": False,
            "engine": "google_cse",
            "results": [
                {"title": "Test Result", "url": "https://example.com", "snippet": "Test snippet"}
            ]
        }
        
        result = web_search.invoke({"query": "test query", "limit": 3})
        
        assert result["error"] is False
        assert result["engine"] == "google_cse"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Result"

    @patch('luminamind.py_tools.web_search._search_google_cse')
    @patch('luminamind.py_tools.web_search._search_serper')
    def test_web_search_fallback_to_serper(self, mock_serper, mock_google):
        """Test fallback to Serper when Google CSE fails."""
        mock_google.return_value = {"skipped": True, "message": "GOOGLE_API_KEY/GOOGLE_CSE_ID not set"}
        mock_serper.return_value = {
            "error": False,
            "engine": "serper",
            "results": [
                {"title": "Serper Result", "url": "https://serper.com", "snippet": "Serper snippet"}
            ]
        }
        
        result = web_search.invoke({"query": "test query"})
        
        assert result["error"] is False
        assert result["engine"] == "serper"
        assert "attempts" in result

    @patch('luminamind.py_tools.web_search._search_google_cse')
    @patch('luminamind.py_tools.web_search._search_serper')
    @patch('luminamind.py_tools.web_search._search_ollama')
    def test_web_search_fallback_to_ollama(self, mock_ollama, mock_serper, mock_google):
        """Test fallback to Ollama when both Google and Serper fail."""
        mock_google.return_value = {"skipped": True, "message": "GOOGLE_API_KEY/GOOGLE_CSE_ID not set"}
        mock_serper.return_value = {"skipped": True, "message": "SERPER_API_KEY not set"}
        mock_ollama.return_value = {
            "error": False,
            "engine": "ollama_search",
            "results": [
                {"title": "Ollama Result", "url": "https://ollama.com", "snippet": "Ollama snippet"}
            ]
        }
        
        result = web_search.invoke({"query": "test query"})
        
        assert result["error"] is False
        assert result["engine"] == "ollama_search"
        assert len(result["attempts"]) == 2

    @patch('luminamind.py_tools.web_search._search_google_cse')
    @patch('luminamind.py_tools.web_search._search_serper')
    @patch('luminamind.py_tools.web_search._search_ollama')
    def test_web_search_all_providers_fail(self, mock_ollama, mock_serper, mock_google):
        """Test behavior when all providers fail."""
        mock_google.return_value = {"error": True, "message": "Google error"}
        mock_serper.return_value = {"error": True, "message": "Serper error"}
        mock_ollama.return_value = {"error": True, "message": "Ollama error"}
        
        result = web_search.invoke({"query": "test query"})
        
        assert result["error"] is True
        assert "attempts" in result
        assert len(result["attempts"]) == 3

    def test_web_search_limit_capping(self):
        """Test that search results are properly capped."""
        # This test verifies the internal _prune_results function
        from luminamind.py_tools.web_search import _prune_results
        
        results = [{"title": f"Result {i}"} for i in range(15)]
        pruned = _prune_results(results, 5)
        
        assert len(pruned) == 5
        assert pruned[0]["title"] == "Result 0"

    def test_web_search_normalize_results(self):
        """Test result normalization."""
        from luminamind.py_tools.web_search import _normalize_results
        
        items = [
            {
                "title": "Test Result",
                "link": "https://example.com",
                "snippet": "Test snippet"
            }
        ]
        
        results = _normalize_results(items)
        
        assert "url" in results[0]
        assert "link" not in results[0]
        assert results[0]["url"] == "https://example.com"

class TestGoogleCSE:
    """Test cases for Google CSE search functionality."""

    @patch('luminamind.py_tools.web_search.requests.get')
    def test_search_google_cse_success(self, mock_get):
        """Test successful Google CSE search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Google Result",
                    "link": "https://google.com",
                    "snippet": "Google snippet"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = _search_google_cse("test query", limit=3)
        
        assert result["error"] is False
        assert result["engine"] == "google_cse"
        assert len(result["results"]) == 1

    @patch('luminamind.py_tools.web_search.requests.get')
    def test_search_google_cse_missing_credentials(self, mock_get):
        """Test Google CSE with missing credentials."""
        with patch('luminamind.py_tools.web_search.GOOGLE_API_KEY', None):
            result = _search_google_cse("test query", limit=5)
            assert result["skipped"] is True
            assert "GOOGLE_API_KEY/GOOGLE_CSE_ID not set" in result["message"]

    @patch('luminamind.py_tools.web_search.requests.get')
    def test_search_google_cse_http_error(self, mock_get):
        """Test Google CSE HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_response.json.return_value = {"error": {"message": "Not found"}}
        mock_get.return_value = mock_response
        
        import requests
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
        
        result = _search_google_cse("test query", limit=5)
        
        assert result["error"] is True
        assert "HTTP 404" in result["message"]

class TestSerper:
    """Test cases for Serper search functionality."""

    @patch('luminamind.py_tools.web_search.requests.post')
    def test_search_serper_success(self, mock_post):
        """Test successful Serper search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Serper Result",
                    "link": "https://serper.com",
                    "snippet": "Serper snippet"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        result = _search_serper("test query", limit=3)
        
        assert result["error"] is False
        assert result["engine"] == "serper"
        assert len(result["results"]) == 1

    @patch('luminamind.py_tools.web_search.requests.post')
    def test_search_serper_missing_credentials(self, mock_post):
        """Test Serper with missing credentials."""
        with patch('luminamind.py_tools.web_search.SERPER_API_KEY', None):
            result = _search_serper("test query", limit=5)
            assert result["skipped"] is True
            assert "SERPER_API_KEY not set" in result["message"]

class TestOllama:
    """Test cases for Ollama search functionality."""

    @patch('luminamind.py_tools.web_search.requests.post')
    def test_search_ollama_success(self, mock_post):
        """Test successful Ollama search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Ollama Result",
                    "url": "https://ollama.com",
                    "text": "Ollama snippet"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        result = _search_ollama("test query", limit=3)
        
        assert result["error"] is False
        assert result["engine"] == "ollama_search"
        assert len(result["results"]) == 1

    @patch('luminamind.py_tools.web_search.requests.post')
    def test_search_ollama_404_error(self, mock_post):
        """Test Ollama with 404 error (endpoint not available)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        result = _search_ollama("test query", limit=5)
        
        assert result["error"] is True
        assert "ollama search endpoint not available" in result["message"]

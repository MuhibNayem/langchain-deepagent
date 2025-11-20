"""Unit tests for the weather tool."""

import pytest
from unittest.mock import patch, Mock
from luminamind.py_tools.weather import get_weather, _fetch_weather

class TestWeather:
    """Test cases for the weather tool."""

    @patch('luminamind.py_tools.weather.requests.get')
    @patch('os.environ.get')
    def test_get_weather_success(self, mock_env, mock_get):
        """Test successful weather retrieval."""
        mock_env.return_value = "fake_api_key"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "location": {"name": "London", "country": "UK"},
            "current": {
                "condition": {"text": "Sunny"},
                "temp_c": 20,
                "temp_f": 68,
                "feelslike_c": 19,
                "feelslike_f": 66,
                "humidity": 50,
                "wind_kph": 10,
                "wind_dir": "N",
                "cloud": 0,
                "last_updated": "2023-01-01 12:00"
            }
        }
        mock_get.return_value = mock_response

        result = get_weather.invoke({"city": "London"})

        assert result["error"] is False
        assert result["location"] == "London"
        assert result["condition"] == "Sunny"
        assert result["temp_c"] == 20

    @patch('os.environ.get')
    def test_get_weather_no_api_key(self, mock_env):
        """Test weather retrieval without API key."""
        mock_env.return_value = None
        result = get_weather.invoke({"city": "London"})
        assert result["error"] is True
        assert "WEATHER_API_KEY is not set" in result["message"]

    def test_get_weather_no_query(self):
        """Test weather retrieval without query."""
        result = get_weather.invoke({})
        assert result["error"] is True
        assert "Provide city, location, or query" in result["message"]

    @patch('luminamind.py_tools.weather.requests.get')
    @patch('os.environ.get')
    def test_get_weather_http_error(self, mock_env, mock_get):
        """Test weather retrieval with HTTP error."""
        mock_env.return_value = "fake_api_key"
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_response.json.return_value = {"error": {"message": "City not found"}}
        mock_get.return_value = mock_response
        
        # We need to simulate requests.HTTPError being raised by raise_for_status
        # However, the code catches requests.HTTPError. 
        # Let's mock requests.get to raise it directly if possible, or mock raise_for_status
        
        import requests
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Client Error")
        
        result = get_weather.invoke({"city": "InvalidCity"})
        
        assert result["error"] is True
        assert "HTTP 404" in result["message"]
        assert "City not found" in result["message"]

    @patch('luminamind.py_tools.weather.requests.get')
    @patch('os.environ.get')
    def test_get_weather_request_exception(self, mock_env, mock_get):
        """Test weather retrieval with generic request exception."""
        mock_env.return_value = "fake_api_key"
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = get_weather.invoke({"city": "London"})
        
        assert result["error"] is True
        assert "Connection failed" in result["message"]

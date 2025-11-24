"""Unit tests for the weather tool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import ClientError
from luminamind.py_tools.weather import get_weather, _fetch_weather


class TestWeather:
    """Test cases for the weather tool."""

    @pytest.mark.asyncio
    @patch('os.environ.get')
    @patch('aiohttp.ClientSession')
    async def test_get_weather_success(self, mock_session_class, mock_env):
        """Test successful weather retrieval."""
        mock_env.return_value = "fake_api_key"
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
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
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        mock_session_class.return_value = mock_session
        
        result = await get_weather.ainvoke({"city": "London"})

        assert result["error"] is False
        assert result["location"] == "London"
        assert result["condition"] == "Sunny"
        assert result["temp_c"] == 20

    @pytest.mark.asyncio
    @patch('os.environ.get')
    async def test_get_weather_no_api_key(self, mock_env):
        """Test weather retrieval without API key."""
        mock_env.return_value = None
        result = await get_weather.ainvoke({"city": "London"})
        assert result["error"] is True
        assert "WEATHER_API_KEY is not set" in result["message"]

    @pytest.mark.asyncio
    async def test_get_weather_no_query(self):
        """Test weather retrieval without query."""
        result = await get_weather.ainvoke({})
        assert result["error"] is True
        assert "Provide city, location, or query" in result["message"]

    @pytest.mark.asyncio
    @patch('os.environ.get')
    @patch('aiohttp.ClientSession')
    async def test_get_weather_http_error(self, mock_session_class, mock_env):
        """Test weather retrieval with HTTP error."""
        mock_env.return_value = "fake_api_key"
        
        # Create a mock response with error status
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": {"message": "City not found"}})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        mock_session_class.return_value = mock_session
        
        result = await get_weather.ainvoke({"city": "InvalidCity"})
        
        assert result["error"] is True
        assert "HTTP 404" in result["message"]
        assert "City not found" in result["message"]

    @pytest.mark.asyncio
    @patch('os.environ.get')
    @patch('aiohttp.ClientSession')
    async def test_get_weather_client_error(self, mock_session_class, mock_env):
        """Test weather retrieval with aiohttp ClientError."""
        mock_env.return_value = "fake_api_key"
        
        # Mock session to raise ClientError
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=ClientError("Connection failed"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        
        mock_session_class.return_value = mock_session
        
        result = await get_weather.ainvoke({"city": "London"})
        
        assert result["error"] is True
        assert "Connection failed" in result["message"]

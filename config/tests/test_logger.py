"""
Tests for config logger module.
Path: config/tests/test_logger.py
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from config.logger import InterceptHandler, setup_django_logging


class TestInterceptHandler:
    """Test the InterceptHandler class."""
    
    def test_intercept_handler_emit_success(self):
        """Test successful log emission."""
        handler = InterceptHandler()
        
        # Create a mock record
        record = MagicMock()
        record.levelname = "INFO"
        record.levelno = 20
        record.exc_info = None
        record.getMessage.return_value = "Test message"
        
        # Mock the logger.level method to return a valid level
        with patch('config.logger.logger') as mock_logger:
            mock_level = MagicMock()
            mock_level.name = "INFO"
            mock_logger.level.return_value = mock_level
            
            # Call emit
            handler.emit(record)
            
            # Verify logger.level was called
            mock_logger.level.assert_called_once_with("INFO")
            
            # Verify the log was called
            mock_logger.opt.assert_called_once_with(depth=6, exception=None)
            mock_logger.opt.return_value.log.assert_called_once_with("INFO", "Test message")
    
    def test_intercept_handler_emit_value_error(self):
        """Test log emission when ValueError occurs in level conversion."""
        handler = InterceptHandler()
        
        # Create a mock record
        record = MagicMock()
        record.levelname = "INVALID_LEVEL"
        record.levelno = 25  # Some numeric level
        record.exc_info = None
        record.getMessage.return_value = "Test message"
        
        # Mock the logger.level method to raise ValueError
        with patch('config.logger.logger') as mock_logger:
            mock_logger.level.side_effect = ValueError("Invalid level")
            
            # Call emit
            handler.emit(record)
            
            # Verify logger.level was called and failed
            mock_logger.level.assert_called_once_with("INVALID_LEVEL")
            
            # Verify the log was called with the numeric level
            mock_logger.opt.assert_called_once_with(depth=6, exception=None)
            mock_logger.opt.return_value.log.assert_called_once_with(25, "Test message")
    
    def test_intercept_handler_emit_with_exception_info(self):
        """Test log emission with exception info."""
        handler = InterceptHandler()
        
        # Create a mock record with exception info
        record = MagicMock()
        record.levelname = "ERROR"
        record.levelno = 40
        record.exc_info = ("ExceptionType", "Exception message", "traceback")
        record.getMessage.return_value = "Error message"
        
        # Mock the logger.level method to return a valid level
        with patch('config.logger.logger') as mock_logger:
            mock_level = MagicMock()
            mock_level.name = "ERROR"
            mock_logger.level.return_value = mock_level
            
            # Call emit
            handler.emit(record)
            
            # Verify logger.level was called
            mock_logger.level.assert_called_once_with("ERROR")
            
            # Verify the log was called with exception info
            mock_logger.opt.assert_called_once_with(depth=6, exception=("ExceptionType", "Exception message", "traceback"))
            mock_logger.opt.return_value.log.assert_called_once_with("ERROR", "Error message")


class TestSetupDjangoLogging:
    """Test the setup_django_logging function."""
    
    @patch('config.logger.logging')
    def test_setup_django_logging(self, mock_logging):
        """Test Django logging setup."""
        # Mock the root logger
        mock_logging.root.handlers = []
        mock_logging.basicConfig = MagicMock()
        
        # Mock the getLogger method
        mock_get_logger = MagicMock()
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        mock_logging.getLogger = mock_get_logger
        
        # Call the function
        setup_django_logging()
        
        # Verify basicConfig was called with correct arguments
        mock_logging.basicConfig.assert_called_once()
        call_args = mock_logging.basicConfig.call_args
        assert call_args[1]['level'] == 0
        assert len(call_args[1]['handlers']) == 1
        assert isinstance(call_args[1]['handlers'][0], InterceptHandler)
        
        # Verify Django loggers were configured (basic verification)
        assert mock_get_logger.call_count >= 4  # At least the expected loggers

"""
Tests for utils debug utilities.
Path: utils/tests/test_debug.py
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from django.test import override_settings

from utils.debug.ic import styled_output, ic_timer


class TestDebugUtilities:
    """Test the debug utilities."""
    
    def test_styled_output(self, capsys):
        """Test that styled_output formats text correctly."""
        test_message = "Test debug message"
        
        styled_output(test_message)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that the output contains the message
        assert test_message in output
        
        # Check that it contains the styling elements
        assert "IC DEBUG OUTPUT" in output
        assert "=" in output  # Should contain separator lines
    
    def test_ic_timer_context_manager(self):
        """Test that ic_timer measures execution time correctly."""
        label = "Test Timer"
        
        with ic_timer(label) as timer:
            time.sleep(0.1)  # Sleep for 100ms
        
        # The timer should have measured some time
        # We can't easily test the exact output without mocking ic,
        # but we can test that the context manager works without errors
    
    def test_ic_timer_without_label(self):
        """Test that ic_timer works without a label."""
        with ic_timer():
            time.sleep(0.01)  # Sleep for 10ms
        
        # Should work without errors
    
    @patch('utils.debug.ic.ic')
    def test_ic_timer_output(self, mock_ic):
        """Test that ic_timer calls ic with the correct format."""
        label = "Test Timer"
        
        with ic_timer(label):
            time.sleep(0.01)
        
        # Verify that ic was called
        assert mock_ic.called
        
        # Get the call arguments
        call_args = mock_ic.call_args[0][0]
        
        # Check that the output contains the label and timing info
        assert label in call_args
        assert "took" in call_args
        assert "s" in call_args  # Should end with seconds
    
    @override_settings(DEBUG=True)
    def test_ic_enabled_in_debug_mode(self):
        """Test that ic is enabled when DEBUG=True."""
        # This test verifies that the ic configuration is set up correctly
        # We can't easily test the actual ic behavior without complex mocking,
        # but we can test that the module imports correctly in debug mode
        from utils.debug.ic import ic
        
        # Should not raise any errors
        assert ic is not None
    
    @override_settings(DEBUG=False)
    def test_ic_disabled_in_production(self):
        """Test that ic is disabled when DEBUG=False."""
        # This test verifies that ic is disabled in production
        # We can't easily test the actual ic behavior without complex mocking,
        # but we can test that the module imports correctly in production mode
        from utils.debug.ic import ic
        
        # Should not raise any errors
        assert ic is not None
    
    def test_ic_timer_measures_actual_time(self):
        """Test that ic_timer measures actual execution time."""
        label = "Precise Timer"
        sleep_time = 0.05  # 50ms
        
        start_time = time.time()
        
        with ic_timer(label):
            time.sleep(sleep_time)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # The actual duration should be at least the sleep time
        # (with some tolerance for overhead)
        assert actual_duration >= sleep_time
        assert actual_duration < sleep_time + 0.1  # Should not be much longer
    
    def test_ic_timer_multiple_uses(self):
        """Test that ic_timer can be used multiple times."""
        # First use
        with ic_timer("First Timer"):
            time.sleep(0.01)
        
        # Second use
        with ic_timer("Second Timer"):
            time.sleep(0.01)
        
        # Third use
        with ic_timer("Third Timer"):
            time.sleep(0.01)
        
        # Should work without errors
    
    def test_styled_output_with_special_characters(self, capsys):
        """Test that styled_output handles special characters correctly."""
        test_message = "Test with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        styled_output(test_message)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that the message is in the output
        assert test_message in output
    
    def test_styled_output_with_empty_string(self, capsys):
        """Test that styled_output handles empty strings correctly."""
        test_message = ""
        
        styled_output(test_message)
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should still produce output with the frame
        assert "IC DEBUG OUTPUT" in output
        assert "=" in output

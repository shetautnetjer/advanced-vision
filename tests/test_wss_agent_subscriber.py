"""Tests for WSSAgentSubscriber."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from collections import deque

from advanced_vision.wss_agent_subscriber import (
    WSSAgentSubscriber,
    subscribe_to_feed,
    FeedPort,
    SchemaType,
    FeedConfig,
    MessageBuffer,
    Subscription,
)


class TestMessageBuffer:
    """Test MessageBuffer functionality."""
    
    def test_add_message(self):
        buffer = MessageBuffer(max_size=10)
        buffer.add({"type": "test", "data": "hello"})
        
        recent = buffer.get_recent(1)
        assert len(recent) == 1
        assert recent[0]["message"]["type"] == "test"
        assert "timestamp" in recent[0]
    
    def test_ring_buffer_overflow(self):
        buffer = MessageBuffer(max_size=3)
        
        for i in range(5):
            buffer.add({"index": i})
        
        recent = buffer.get_recent(10)
        assert len(recent) == 3
        # Should contain indices 2, 3, 4
        assert recent[0]["message"]["index"] == 2
        assert recent[2]["message"]["index"] == 4
    
    def test_clear(self):
        buffer = MessageBuffer(max_size=10)
        buffer.add({"test": "data"})
        buffer.clear()
        
        assert len(buffer.get_recent(10)) == 0


class TestFeedConfig:
    """Test FeedConfig dataclass."""
    
    def test_uri_generation(self):
        config = FeedConfig(
            port=8004,
            schema=SchemaType.TRADING,
            host="localhost",
            path="/ws"
        )
        assert config.uri == "ws://localhost:8004/ws"
    
    def test_default_path(self):
        config = FeedConfig(
            port=8002,
            schema=SchemaType.UI
        )
        assert config.uri == "ws://localhost:8002/"


class TestWSSAgentSubscriber:
    """Test WSSAgentSubscriber functionality."""
    
    def test_initialization(self):
        sub = WSSAgentSubscriber(
            host="127.0.0.1",
            buffer_size=50,
            reconnect_delay=10.0
        )
        
        assert sub.host == "127.0.0.1"
        assert sub.buffer_size == 50
        assert sub.reconnect_delay == 10.0
        assert not sub.is_running()
    
    def test_subscribe(self):
        sub = WSSAgentSubscriber()
        callback = Mock()
        
        sub.subscribe(8004, schema="trading", callback=callback)
        
        assert 8004 in sub._subscriptions
        assert sub._subscriptions[8004].config.schema == SchemaType.TRADING
        assert sub._subscriptions[8004].config.callback == callback
    
    def test_subscribe_to_feed_by_name(self):
        sub = WSSAgentSubscriber()
        
        sub.subscribe_to_feed("eagle", schema="trading")
        
        assert FeedPort.EAGLE.value in sub._subscriptions
    
    def test_subscribe_to_feed_invalid_name(self):
        sub = WSSAgentSubscriber()
        
        with pytest.raises(ValueError, match="Unknown feed"):
            sub.subscribe_to_feed("invalid_feed")
    
    def test_add_remove_global_callback(self):
        sub = WSSAgentSubscriber()
        callback = Mock()
        
        sub.add_global_callback(callback)
        assert callback in sub._global_callbacks
        
        sub.remove_global_callback(callback)
        assert callback not in sub._global_callbacks
    
    def test_add_event_filter(self):
        sub = WSSAgentSubscriber()
        filter_fn = Mock(return_value=True)
        
        sub.add_event_filter("pattern", filter_fn)
        assert "pattern" in sub._event_filters
    
    def test_get_statistics_empty(self):
        sub = WSSAgentSubscriber()
        stats = sub.get_statistics()
        
        assert stats["total_messages"] == 0
        assert stats["total_errors"] == 0
        assert stats["subscriptions"] == {}
    
    def test_should_process_message_both_schema(self):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="both")
        subscription = sub._subscriptions[8004]
        
        assert sub._should_process_message(subscription, {"type": "anything"})
    
    def test_should_process_message_ui_schema(self):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="ui")
        subscription = sub._subscriptions[8004]
        
        assert sub._should_process_message(subscription, {"schema": "ui"})
        assert sub._should_process_message(subscription, {"type": "navigation"})
        assert not sub._should_process_message(subscription, {"schema": "trading"})
    
    def test_should_process_message_trading_schema(self):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="trading")
        subscription = sub._subscriptions[8004]
        
        assert sub._should_process_message(subscription, {"schema": "trading"})
        assert sub._should_process_message(subscription, {"type": "pattern"})
        assert sub._should_process_message(subscription, {"type": "signal"})
        assert not sub._should_process_message(subscription, {"schema": "ui"})
    
    def test_get_feed_name(self):
        sub = WSSAgentSubscriber()
        
        assert sub._get_feed_name(8002) == "yolo"
        assert sub._get_feed_name(8003) == "sam"
        assert sub._get_feed_name(8004) == "eagle"
        assert sub._get_feed_name(8005) == "analysis"
        assert sub._get_feed_name(9999) == "unknown"
    
    def test_get_recent_messages(self):
        sub = WSSAgentSubscriber(buffer_size=10)
        sub._buffer.add({"port": 8004, "feed": "eagle", "type": "test"})
        
        recent = sub.get_recent_messages(count=5)
        assert len(recent) == 1
        assert recent[0]["message"]["type"] == "test"
    
    def test_is_connected(self):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="trading")
        
        # Not running, should be False
        assert not sub.is_connected()
        assert not sub.is_connected(8004)
    
    def test_start_stop(self):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="trading")
        
        sub.start()
        assert sub.is_running()
        
        sub.stop()
        assert not sub.is_running()


class TestSubscribeToFeedHelper:
    """Test the subscribe_to_feed convenience function."""
    
    @patch.object(WSSAgentSubscriber, 'start')
    def test_quick_subscribe(self, mock_start):
        callback = Mock()
        
        sub = subscribe_to_feed(
            port=8004,
            schema="trading",
            callback=callback,
            host="127.0.0.1"
        )
        
        assert isinstance(sub, WSSAgentSubscriber)
        assert 8004 in sub._subscriptions
        assert sub._subscriptions[8004].config.callback == callback
        mock_start.assert_called_once()


class TestAsyncOperations:
    """Test async functionality using event loop."""
    
    @pytest.fixture
    def event_loop(self):
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    def test_handle_message_valid_json(self, event_loop):
        sub = WSSAgentSubscriber()
        callback = Mock()
        sub.subscribe(8004, schema="both", callback=callback)
        
        subscription = sub._subscriptions[8004]
        
        event_loop.run_until_complete(
            sub._handle_message(8004, subscription, '{"type": "test", "data": "value"}')
        )
        
        assert subscription.message_count == 1
        callback.assert_called_once()
    
    def test_handle_message_invalid_json(self, event_loop):
        sub = WSSAgentSubscriber()
        sub.subscribe(8004, schema="both")
        subscription = sub._subscriptions[8004]
        
        event_loop.run_until_complete(
            sub._handle_message(8004, subscription, "invalid json{")
        )
        
        assert subscription.error_count == 1
    
    def test_handle_message_schema_filter(self, event_loop):
        sub = WSSAgentSubscriber()
        callback = Mock()
        sub.subscribe(8004, schema="trading", callback=callback)
        
        subscription = sub._subscriptions[8004]
        
        # This message should be filtered out (ui schema)
        event_loop.run_until_complete(
            sub._handle_message(8004, subscription, '{"schema": "ui", "data": "value"}')
        )
        
        # Callback should not be called due to schema filter
        callback.assert_not_called()
        # But message is still counted and buffered
        assert subscription.message_count == 1
    
    def test_handle_message_event_filter(self, event_loop):
        sub = WSSAgentSubscriber()
        callback = Mock()
        sub.subscribe(8004, schema="both", callback=callback)
        sub.add_event_filter("pattern", lambda m: m.get("confidence", 0) > 0.5)
        
        subscription = sub._subscriptions[8004]
        
        # Low confidence - should be filtered
        event_loop.run_until_complete(
            sub._handle_message(8004, subscription, '{"type": "pattern", "confidence": 0.3}')
        )
        callback.assert_not_called()
        
        # High confidence - should pass through
        event_loop.run_until_complete(
            sub._handle_message(8004, subscription, '{"type": "pattern", "confidence": 0.8}')
        )
        callback.assert_called_once()

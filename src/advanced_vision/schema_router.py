#!/usr/bin/env python3
"""
Schema Router for Advanced Vision
Routes messages to UI schema or Trading schema based on content type
"""

import json
import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path


class SchemaType(Enum):
    """Available schema types"""
    UI = "ui"
    TRADING = "trading"
    UNKNOWN = "unknown"


class UIElementType(Enum):
    """UI element types"""
    NAVIGATION = "navigation"
    BUTTON = "button"
    FORM = "form"
    INPUT = "input"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    LINK = "link"
    IMAGE = "image"
    TEXT = "text"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class TradingPatternType(Enum):
    """Trading pattern types"""
    TREND = "trend"
    REVERSAL = "reversal"
    BREAKOUT = "breakout"
    SUPPORT_RESISTANCE = "support_resistance"
    SIGNAL = "signal"
    RISK_EVENT = "risk_event"
    PRICE_ACTION = "price_action"
    VOLUME_SPIKE = "volume_spike"
    UNKNOWN = "unknown"


@dataclass
class UISchema:
    """UI Schema for interface elements"""
    element_type: UIElementType
    element_id: Optional[str] = None
    label: Optional[str] = None
    location: Dict[str, int] = field(default_factory=dict)  # x, y, width, height
    properties: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "schema_type": "ui",
            "element_type": self.element_type.value,
            "element_id": self.element_id,
            "label": self.label,
            "location": self.location,
            "properties": self.properties,
            "actions": self.actions
        }


@dataclass
class TradingSchema:
    """Trading Schema for market analysis"""
    pattern_type: TradingPatternType
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    confidence: float = 0.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "schema_type": "trading",
            "pattern_type": self.pattern_type.value,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "metadata": self.metadata
        }


@dataclass
class RoutingResult:
    """Result of schema routing"""
    schema_type: SchemaType
    schema_data: Optional[Union[UISchema, TradingSchema]] = None
    confidence: float = 0.0
    source_feed: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "schema_type": self.schema_type.value,
            "schema_data": self.schema_data.to_dict() if self.schema_data else None,
            "confidence": self.confidence,
            "source_feed": self.source_feed,
            "timestamp": self.timestamp
        }


class SchemaRouter:
    """Routes messages to appropriate schema based on content analysis"""
    
    # UI-related keywords
    UI_KEYWORDS = {
        UIElementType.NAVIGATION: ["nav", "menu", "sidebar", "navbar", "breadcrumb", "tab"],
        UIElementType.BUTTON: ["button", "click", "submit", "action", "btn"],
        UIElementType.FORM: ["form", "fieldset", "login", "signup", "register"],
        UIElementType.INPUT: ["input", "textfield", "textarea", "search", "password"],
        UIElementType.DROPDOWN: ["dropdown", "select", "combo", "listbox", "menu"],
        UIElementType.CHECKBOX: ["checkbox", "check", "toggle", "switch"],
        UIElementType.RADIO: ["radio", "option", "choice"],
        UIElementType.LINK: ["link", "anchor", "href", "url"],
        UIElementType.IMAGE: ["image", "img", "picture", "icon", "logo"],
        UIElementType.TEXT: ["text", "label", "heading", "paragraph", "span"],
        UIElementType.CONTAINER: ["div", "section", "container", "panel", "card"]
    }
    
    # Trading-related keywords
    TRADING_KEYWORDS = {
        TradingPatternType.TREND: ["trend", "uptrend", "downtrend", "bullish", "bearish", "direction"],
        TradingPatternType.REVERSAL: ["reversal", "reverse", "turn", "pivot", "change"],
        TradingPatternType.BREAKOUT: ["breakout", "break", "breakthrough", "escape", "momentum"],
        TradingPatternType.SUPPORT_RESISTANCE: ["support", "resistance", "level", "floor", "ceiling"],
        TradingPatternType.SIGNAL: ["signal", "alert", "indicator", "trigger", "entry"],
        TradingPatternType.RISK_EVENT: ["risk", "stop", "loss", "drawdown", "volatility", "event"],
        TradingPatternType.PRICE_ACTION: ["price", "candle", "wick", "body", "chart"],
        TradingPatternType.VOLUME_SPIKE: ["volume", "spike", "surge", "liquidity"]
    }
    
    def __init__(self):
        self.custom_rules: List[Callable[[dict], Optional[RoutingResult]]] = []
        self.schema_configs: Dict[str, Any] = {}
        
    def load_schemas(self, config: dict):
        """Load schema configurations"""
        self.schema_configs = config
        
    def add_custom_rule(self, rule: Callable[[dict], Optional[RoutingResult]]):
        """Add a custom routing rule"""
        self.custom_rules.append(rule)
        
    def route_message(self, feed_name: str, data: dict, timestamp: str) -> RoutingResult:
        """Route a JSON message to appropriate schema"""
        # Check custom rules first
        for rule in self.custom_rules:
            result = rule(data)
            if result:
                result.source_feed = feed_name
                return result
                
        # Analyze content
        text_content = json.dumps(data).lower()
        
        # Try UI detection
        ui_schema = self._detect_ui_schema(data, text_content)
        if ui_schema:
            return RoutingResult(
                schema_type=SchemaType.UI,
                schema_data=ui_schema,
                confidence=0.8,
                source_feed=feed_name,
                timestamp=timestamp
            )
            
        # Try Trading detection
        trading_schema = self._detect_trading_schema(data, text_content)
        if trading_schema:
            return RoutingResult(
                schema_type=SchemaType.TRADING,
                schema_data=trading_schema,
                confidence=0.8,
                source_feed=feed_name,
                timestamp=timestamp
            )
            
        # Unknown schema type
        return RoutingResult(
            schema_type=SchemaType.UNKNOWN,
            confidence=0.0,
            source_feed=feed_name,
            timestamp=timestamp
        )
        
    def route_binary(self, feed_name: str, data: bytes, timestamp: str) -> RoutingResult:
        """Route binary data (typically frames)"""
        # Binary data usually goes through processing pipelines
        # Route based on feed name
        if "capture" in feed_name.lower():
            return RoutingResult(
                schema_type=SchemaType.UI,  # Raw frames often contain UI
                schema_data=UISchema(
                    element_type=UIElementType.IMAGE,
                    properties={"size_bytes": len(data), "format": "binary"}
                ),
                confidence=0.5,
                source_feed=feed_name,
                timestamp=timestamp
            )
        elif any(x in feed_name.lower() for x in ["yolo", "detection"]):
            return RoutingResult(
                schema_type=SchemaType.UI,
                schema_data=UISchema(
                    element_type=UIElementType.CONTAINER,
                    properties={"detection_frame": True, "size_bytes": len(data)}
                ),
                confidence=0.6,
                source_feed=feed_name,
                timestamp=timestamp
            )
        else:
            return RoutingResult(
                schema_type=SchemaType.UNKNOWN,
                confidence=0.3,
                source_feed=feed_name,
                timestamp=timestamp
            )
            
    def _detect_ui_schema(self, data: dict, text_content: str) -> Optional[UISchema]:
        """Detect UI schema from message content"""
        scores = {}
        
        for element_type, keywords in self.UI_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_content)
            if score > 0:
                scores[element_type] = score
                
        if not scores:
            return None
            
        # Get highest scoring element type
        best_type = max(scores, key=scores.get)
        
        # Extract UI-specific fields
        element_id = data.get("id") or data.get("element_id")
        label = data.get("label") or data.get("text") or data.get("name")
        
        location = {}
        for key in ["x", "y", "width", "height", "top", "left", "right", "bottom"]:
            if key in data:
                location[key] = data[key]
                
        # Extract actions
        actions = []
        if "actions" in data:
            actions = data["actions"] if isinstance(data["actions"], list) else [data["actions"]]
        elif "click" in text_content:
            actions.append("click")
        elif "submit" in text_content:
            actions.append("submit")
            
        return UISchema(
            element_type=best_type,
            element_id=element_id,
            label=label,
            location=location,
            properties={k: v for k, v in data.items() if k not in ["id", "label", "text", "actions"]},
            actions=actions
        )
        
    def _detect_trading_schema(self, data: dict, text_content: str) -> Optional[TradingSchema]:
        """Detect Trading schema from message content"""
        scores = {}
        
        for pattern_type, keywords in self.TRADING_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_content)
            if score > 0:
                scores[pattern_type] = score
                
        if not scores:
            return None
            
        # Get highest scoring pattern type
        best_type = max(scores, key=scores.get)
        
        # Extract trading-specific fields
        symbol = data.get("symbol") or data.get("ticker") or data.get("pair")
        timeframe = data.get("timeframe") or data.get("period") or data.get("interval")
        confidence = data.get("confidence", 0.5)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence.replace("%", "")) / 100
            except ValueError:
                confidence = 0.5
                
        entry = data.get("entry") or data.get("entry_price")
        stop = data.get("stop") or data.get("stop_loss")
        take_profit = data.get("take_profit") or data.get("target")
        
        # Calculate risk/reward if we have the data
        risk_reward = data.get("risk_reward") or data.get("rr")
        if risk_reward is None and entry and stop and take_profit:
            try:
                entry_f = float(entry)
                stop_f = float(stop)
                tp_f = float(take_profit)
                risk = abs(entry_f - stop_f)
                reward = abs(tp_f - entry_f)
                if risk > 0:
                    risk_reward = reward / risk
            except (ValueError, TypeError):
                pass
                
        return TradingSchema(
            pattern_type=best_type,
            symbol=symbol,
            timeframe=timeframe,
            confidence=confidence,
            entry_price=float(entry) if entry else None,
            stop_loss=float(stop) if stop else None,
            take_profit=float(take_profit) if take_profit else None,
            risk_reward=risk_reward,
            metadata={k: v for k, v in data.items() if k not in [
                "symbol", "ticker", "pair", "timeframe", "period", "interval",
                "confidence", "entry", "entry_price", "stop", "stop_loss",
                "take_profit", "target", "risk_reward", "rr"
            ]}
        )
        
    def classify_feed(self, feed_name: str) -> SchemaType:
        """Classify a feed name to likely schema type"""
        feed_lower = feed_name.lower()
        
        # UI-related feeds
        if any(x in feed_lower for x in ["ui", "capture", "screen", "interface", "nav"]):
            return SchemaType.UI
            
        # Trading-related feeds
        if any(x in feed_lower for x in ["trade", "market", "signal", "price", "chart", "analysis"]):
            return SchemaType.TRADING
            
        return SchemaType.UNKNOWN


# Type hint for Union
from typing import Union


def demo_routing():
    """Demonstrate schema routing"""
    router = SchemaRouter()
    
    # Test UI message
    ui_message = {
        "id": "submit-btn",
        "type": "button",
        "label": "Submit Form",
        "x": 100,
        "y": 200,
        "width": 120,
        "height": 40,
        "actions": ["click", "submit"]
    }
    
    result = router.route_message("capture", ui_message, datetime.utcnow().isoformat())
    print("UI Message Routing:")
    print(json.dumps(result.to_dict(), indent=2))
    print()
    
    # Test Trading message
    trading_message = {
        "symbol": "BTCUSDT",
        "timeframe": "1H",
        "pattern": "breakout",
        "confidence": 0.85,
        "entry": 45000,
        "stop_loss": 44000,
        "take_profit": 47000,
        "risk_reward": 2.0
    }
    
    result = router.route_message("reviewers", trading_message, datetime.utcnow().isoformat())
    print("Trading Message Routing:")
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    demo_routing()

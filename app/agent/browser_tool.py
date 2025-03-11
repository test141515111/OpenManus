"""Browser tool for Manus agent"""
import base64
import json
import os
import time
import requests
from loguru import logger
from app.agent.toolcall import Tool

class BrowserTool(Tool):
    """Tool for browser interactions with screenshot sharing"""
    
    def __init__(self):
        super().__init__(
            name="browser_use",
            description="Use browser to navigate and interact with web pages",
            parameters={
                "url": {
                    "type": "string",
                    "description": "URL to navigate to"
                },
                "actions": {
                    "type": "array",
                    "description": "List of browser actions to perform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["click", "type", "navigate", "screenshot"]
                            },
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the element"
                            },
                            "value": {
                                "type": "string",
                                "description": "Value to type (for type action)"
                            }
                        }
                    }
                }
            }
        )
        
        # Initialize browser-use
        self.browser = None
        try:
            from browser_use import BrowserUse
            self.browser = BrowserUse()
            logger.info("Browser-use initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser-use: {e}")
    
    def _execute(self, **kwargs):
        """Execute browser actions"""
        if self.browser is None:
            return "Browser-use is not initialized"
        
        url = kwargs.get("url")
        actions = kwargs.get("actions", [])
        
        results = []
        
        try:
            # Navigate to URL if provided
            if url:
                logger.info(f"Navigating to {url}")
                self.browser.goto(url)
                results.append(f"Navigated to {url}")
                
                # Take initial screenshot
                self._take_and_share_screenshot()
            
            # Execute actions
            for action in actions:
                action_type = action.get("type")
                selector = action.get("selector")
                value = action.get("value")
                
                if action_type == "click" and selector:
                    logger.info(f"Clicking on {selector}")
                    self.browser.click(selector)
                    results.append(f"Clicked on {selector}")
                
                elif action_type == "type" and selector and value:
                    logger.info(f"Typing '{value}' into {selector}")
                    self.browser.fill(selector, value)
                    results.append(f"Typed '{value}' into {selector}")
                
                elif action_type == "navigate" and value:
                    logger.info(f"Navigating to {value}")
                    self.browser.goto(value)
                    results.append(f"Navigated to {value}")
                
                elif action_type == "screenshot":
                    self._take_and_share_screenshot()
                    results.append("Screenshot taken")
                
                # Wait a bit between actions
                time.sleep(1)
            
            # Take final screenshot
            self._take_and_share_screenshot()
            
            # Get page content
            content = self.browser.get_page_content()
            results.append(f"Page content: {content[:500]}...")
            
            return "\n".join(results)
        
        except Exception as e:
            logger.error(f"Error executing browser actions: {e}")
            return f"Error: {str(e)}"
    
    def _take_and_share_screenshot(self):
        """Take a screenshot and share it with the web UI"""
        try:
            # Take screenshot
            screenshot_path = "/tmp/browser_screenshot.png"
            self.browser.screenshot(screenshot_path)
            
            # Read screenshot and encode as base64
            with open(screenshot_path, "rb") as f:
                screenshot_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Share screenshot with web UI
            try:
                requests.post(
                    "http://localhost:8080/api/browser_screenshot",
                    json={"screenshot": screenshot_data},
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to share screenshot with web UI: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return False

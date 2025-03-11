"""Browser tool for OpenManus with screenshot sharing and video embedding"""
import base64
import os
import time
import asyncio
import tempfile
from pathlib import Path
import aiohttp
from browser_use import Browser
from browser_use import BrowserConfig

class BrowserTool:
    """Tool for browser interactions with screenshot sharing and video recording"""
    
    def __init__(self, screenshot_endpoint="http://localhost:8080/api/browser_screenshot", 
                 video_endpoint="http://localhost:8080/api/browser_video"):
        self.screenshot_endpoint = screenshot_endpoint
        self.video_endpoint = video_endpoint
        self.browser = None
        self.context = None
        self.recording = False
        self.video_path = None
        self.initialize()
        
    def initialize(self):
        """Initialize browser-use"""
        try:
            # Use headless mode to support video recording in environments without X server
            self.browser = Browser(BrowserConfig(headless=True))
            print("Browser initialized successfully")
        except Exception as e:
            print(f"Failed to initialize browser: {e}")
    
    async def new_context(self):
        """Create a new browser context"""
        if not self.browser:
            self.initialize()
            if not self.browser:
                print("Failed to initialize browser")
                return None
        
        if self.context:
            await self.context.close()
        
        # Create a context with video recording configuration
        from browser_use.browser.context import BrowserContextConfig
        
        # Create temp file for video if recording is enabled
        if self.recording:
            self.video_path = tempfile.mktemp(suffix=".webm")
            config = BrowserContextConfig(save_recording_path=self.video_path)
        else:
            config = BrowserContextConfig()
            
        try:
            self.context = await self.browser.new_context(config)
            return self.context
        except Exception as e:
            print(f"Failed to create browser context: {e}")
            return None
    
    async def goto(self, url):
        """Navigate to URL"""
        if not self.context:
            await self.new_context()
            if not self.context:
                return "Failed to create browser context"
        
        try:
            await self.context.navigate_to(url)
            await self.take_and_share_screenshot()
            return f"Navigated to {url}"
        except Exception as e:
            print(f"Failed to navigate to {url}: {e}")
            return f"Failed to navigate to {url}: {e}"
    
    async def click(self, selector):
        """Click on element"""
        if not self.context:
            return "Browser context not initialized"
        
        try:
            element = await self.context.get_dom_element_by_selector(selector)
            if not element:
                return f"Element with selector {selector} not found"
            
            await self.context._click_element_node(element)
            await self.take_and_share_screenshot()
            return f"Clicked on {selector}"
        except Exception as e:
            print(f"Failed to click on {selector}: {e}")
            return f"Failed to click on {selector}: {e}"
    
    async def fill(self, selector, value):
        """Fill input field"""
        if not self.context:
            return "Browser context not initialized"
        
        try:
            element = await self.context.get_dom_element_by_selector(selector)
            if not element:
                return f"Element with selector {selector} not found"
            
            await self.context._input_text_element_node(element, value)
            await self.take_and_share_screenshot()
            return f"Filled {selector} with '{value}'"
        except Exception as e:
            print(f"Failed to fill {selector}: {e}")
            return f"Failed to fill {selector}: {e}"
    
    async def get_page_content(self):
        """Get page content"""
        if not self.context:
            return "Browser context not initialized"
        
        try:
            return await self.context.get_page_html()
        except Exception as e:
            print(f"Failed to get page content: {e}")
            return f"Failed to get page content: {e}"
    
    async def screenshot(self, path=None):
        """Take screenshot"""
        if not self.context:
            return "Browser context not initialized"
        
        if not path:
            path = "/tmp/browser_screenshot.png"
        
        try:
            screenshot_data = await self.context.take_screenshot(full_page=True)
            
            # Save screenshot to file
            with open(path, "wb") as f:
                f.write(screenshot_data)
                
            return path
        except Exception as e:
            print(f"Failed to take screenshot: {e}")
            return f"Failed to take screenshot: {e}"
    
    async def start_recording(self):
        """Start video recording"""
        if self.recording:
            return "Already recording"
        
        # Set recording flag and create a new context with recording enabled
        self.recording = True
        
        # Close existing context if any
        if self.context:
            await self.context.close()
            self.context = None
            
        # Create new context with recording enabled
        await self.new_context()
        
        print(f"Started recording to {self.video_path}")
        return True
    
    async def stop_recording_and_share(self):
        """Stop video recording and share with web UI"""
        if not self.recording or not self.video_path:
            return "Not recording"
        
        try:
            # Close the context to stop recording and save the video
            if self.context:
                await self.context.close()
                self.context = None
            
            self.recording = False
            
            # Wait for video file to be written
            await asyncio.sleep(2)
            
            # Check if video file exists
            if not os.path.exists(self.video_path):
                print(f"Video file not found at {self.video_path}")
                return False
                
            # Read video and encode as base64
            with open(self.video_path, "rb") as f:
                video_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Share video with web UI
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.video_endpoint,
                        json={"video": video_data},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            print(f"Video shared with endpoint: {self.video_endpoint}")
                        else:
                            print(f"Failed to share video with web UI: {await response.text()}")
            except Exception as e:
                print(f"Failed to share video with web UI: {e}")
            
            return True
        except Exception as e:
            print(f"Failed to stop recording: {e}")
            return False
    
    async def take_and_share_screenshot(self):
        """Take screenshot and share with web UI"""
        try:
            screenshot_path = await self.screenshot()
            
            # Read screenshot and encode as base64
            with open(screenshot_path, "rb") as f:
                screenshot_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Share screenshot with web UI
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.screenshot_endpoint,
                        json={"screenshot": screenshot_data},
                        timeout=5
                    ) as response:
                        if response.status == 200:
                            print(f"Screenshot shared with endpoint: {self.screenshot_endpoint}")
                        else:
                            print(f"Failed to share screenshot with web UI: {await response.text()}")
            except Exception as e:
                print(f"Failed to share screenshot with web UI: {e}")
            
            return True
        except Exception as e:
            print(f"Failed to take screenshot: {e}")
            return False
    
    async def close(self):
        """Close browser"""
        if self.recording:
            await self.stop_recording_and_share()
        
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None

"""Web Search Report Tool for OpenManus."""
import asyncio
import base64
import time
from typing import Dict, List, Optional, Any, Union

from app.tool.base import BaseTool
from app.tool.browser_use_tool import BrowserUseTool

class WebSearchReportTool(BaseTool):
    """Tool for performing web searches and generating reports with screenshots."""
    
    name = "web_search_report"
    description = "Performs web searches and generates reports with screenshots."
    
    def __init__(self):
        """Initialize the Web Search Report Tool."""
        super().__init__()
        self.browser_tool = None
    
    async def _ensure_browser_tool(self) -> "BrowserUseTool":
        """Ensure the browser tool is initialized."""
        if self.browser_tool is None:
            # Import here to avoid circular imports
            from app.tool.browser_use_tool import BrowserUseTool
            self.browser_tool = BrowserUseTool()
            # Initialize the browser to avoid None errors
            if self.browser_tool is not None:
                try:
                    await self.browser_tool._ensure_browser_initialized()
                except Exception as e:
                    print(f"Error initializing browser tool: {e}")
        return self.browser_tool
    
    async def execute(
        self,
        query: str,
        num_results: int = 3,
        language: str = "ja",
        include_images: bool = True,
    ) -> Any:
        """
        Execute a web search and generate a report with screenshots.
        
        Args:
            query: The search query to execute
            num_results: Number of results to include in the report (1-5)
            language: Language for search results (ja/en)
            include_images: Whether to include screenshots of search results
            
        Returns:
            A report object containing search results and screenshots
        """
        try:
            # Validate parameters
            if not query:
                return {"error": "検索クエリを入力してください"}
            
            if num_results < 1 or num_results > 5:
                return {"error": "結果の数は1から5の間で指定してください"}
            
            # Initialize browser tool
            browser_tool = await self._ensure_browser_tool()
            if browser_tool is None:
                return {"error": "ブラウザツールの初期化に失敗しました"}
            
            # Prepare search URL based on language
            search_engine = "https://www.google.co.jp/search" if language == "ja" else "https://www.google.com/search"
            search_url = f"{search_engine}?q={query}&hl={language}"
            
            # Navigate to search page
            try:
                await browser_tool.execute(action="navigate", url=search_url)
            except Exception as e:
                return {"error": f"検索ページへの移動に失敗しました: {str(e)}"}
            
            # Take screenshot of search results
            search_screenshot = None
            try:
                screenshot_result = await browser_tool.execute(action="screenshot")
                if hasattr(screenshot_result, 'screenshot') and screenshot_result.screenshot:
                    search_screenshot = screenshot_result.screenshot
            except Exception as e:
                print(f"Error taking search screenshot: {e}")
            
            # Extract search results
            results = []
            try:
                # Wait for search results to load
                await asyncio.sleep(2)
                
                # Get search result elements
                page_content = await browser_tool.execute(action="get_page_content")
                
                # Extract search result links
                links = []
                if hasattr(page_content, 'content'):
                    # Parse content to find result links
                    # This is a simplified version - in a real implementation,
                    # we would use proper HTML parsing
                    content_lines = page_content.content.split('\n')
                    for i, line in enumerate(content_lines):
                        if '<h3' in line and 'href="' in line and i < len(content_lines) - 2:
                            # Extract URL and title
                            url_start = line.find('href="') + 6
                            url_end = line.find('"', url_start)
                            if url_start > 6 and url_end > url_start:
                                url = line[url_start:url_end]
                                if url.startswith('http') and not url.startswith('https://www.google.'):
                                    links.append(url)
                
                # Limit to requested number of results
                links = links[:num_results]
                
                # Visit each result page and collect information
                for i, url in enumerate(links):
                    if i >= num_results:
                        break
                        
                    result = {
                        "url": url,
                        "title": "",
                        "snippet": "",
                        "content": "",
                        "screenshot": None
                    }
                    
                    try:
                        # Navigate to result page
                        await browser_tool.execute(action="navigate", url=url)
                        
                        # Wait for page to load
                        await asyncio.sleep(2)
                        
                        # Get page title
                        title_result = await browser_tool.execute(action="get_page_title")
                        if hasattr(title_result, 'title'):
                            result["title"] = title_result.title
                        
                        # Get page content
                        content_result = await browser_tool.execute(action="get_page_content")
                        if hasattr(content_result, 'content'):
                            # Extract a snippet (first 200 characters of text)
                            text_content = content_result.content.replace('\n', ' ').replace('\t', ' ')
                            result["snippet"] = text_content[:200] + "..."
                            
                            # Store full content (limited to avoid excessive data)
                            result["content"] = text_content[:1000] + "..."
                        
                        # Take screenshot if requested
                        if include_images:
                            screenshot_result = await browser_tool.execute(action="screenshot")
                            if hasattr(screenshot_result, 'screenshot') and screenshot_result.screenshot:
                                result["screenshot"] = screenshot_result.screenshot
                    
                    except Exception as e:
                        result["error"] = f"ページの取得中にエラーが発生しました: {str(e)}"
                    
                    results.append(result)
                    
                    # Go back to search results
                    await browser_tool.execute(action="navigate", url=search_url)
                    await asyncio.sleep(1)
                
            except Exception as e:
                return {"error": f"検索結果の取得中にエラーが発生しました: {str(e)}"}
            
            # Create report
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            report = {
                "query": query,
                "timestamp": timestamp,
                "num_results": num_results,
                "language": language,
                "search_screenshot": search_screenshot,
                "results": results
            }
            
            return {"report": report}
            
        except Exception as e:
            return {"error": f"検索レポートの生成中にエラーが発生しました: {str(e)}"}

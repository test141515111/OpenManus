"""Web Search Report Tool for OpenManus."""
import asyncio
import base64
import io
import json
import time
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from PIL import Image
import aiohttp
from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.tool.browser_use_tool import BrowserUseTool


class WebSearchReportTool(BaseTool):
    """Tool for performing web searches and generating comprehensive reports."""

    name: str = "web_search_report"
    description: str = """
    検索クエリに基づいてウェブ検索を実行し、結果の詳細なレポートを生成します。
    検索結果のスクリーンショット、テキスト内容の要約、および関連リンクを含みます。
    情報収集や調査タスクに使用してください。
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "検索したいクエリまたは質問",
            },
            "num_results": {
                "type": "integer",
                "description": "取得する検索結果の数（1〜5）",
            },
            "language": {
                "type": "string",
                "description": "検索結果の言語（例：ja, en）",
            },
            "include_images": {
                "type": "boolean",
                "description": "検索結果にイメージを含めるかどうか",
            },
        },
        "required": ["query"],
    }

    browser_tool: Optional[BrowserUseTool] = Field(default=None)
    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)

    async def _ensure_browser_tool(self) -> "BrowserUseTool":
        """Ensure the browser tool is initialized."""
        if self.browser_tool is None:
            # Import here to avoid circular imports
            from app.tool.browser_use_tool import BrowserUseTool
            self.browser_tool = BrowserUseTool()
        
        # Make sure we have a valid browser tool
        if self.browser_tool is None:
            raise ValueError("Failed to initialize browser tool")
            
        # Initialize the browser context
        try:
            await self.browser_tool._ensure_browser_initialized()
        except Exception as e:
            print(f"Error initializing browser tool: {e}")
            raise ValueError(f"ブラウザツールの初期化に失敗しました: {e}")
            
        return self.browser_tool

    async def execute(
        self,
        query: str,
        num_results: int = 3,
        language: str = "ja",
        include_images: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        Execute web search and generate a report.

        Args:
            query: Search query or question
            num_results: Number of search results to include (1-5)
            language: Language for search results (e.g., ja, en)
            include_images: Whether to include images in the report
            **kwargs: Additional arguments

        Returns:
            ToolResult with the search report
        """
        async with self.lock:
            try:
                # Validate parameters
                if num_results < 1 or num_results > 5:
                    return ToolResult(error="検索結果の数は1から5の間で指定してください")
                
                # Initialize browser tool
                browser = await self._ensure_browser_tool()
                
                # Construct search URL with language preference
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl={language}"
                
                # Navigate to search page
                await browser.execute(action="navigate", url=search_url)
                
                # Take screenshot of search results
                screenshot_result = await browser.execute(action="screenshot")
                screenshot_base64 = None
                if hasattr(screenshot_result, 'output') and screenshot_result.output:
                    screenshot_base64 = screenshot_result.output
                
                # Get HTML content
                html_result = await browser.execute(action="get_html")
                html_content = ""
                if hasattr(html_result, 'output') and html_result.output:
                    html_content = html_result.output
                
                # Parse search results
                search_results = self._parse_search_results(html_content, num_results)
                
                # Visit each result page and collect data if needed
                detailed_results = []
                for i, result in enumerate(search_results):
                    if i >= num_results:
                        break
                    
                    detailed_result = {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                    }
                    
                    # Visit the page to get more details
                    if result.get("url"):
                        try:
                            # Navigate to the result page
                            await browser.execute(action="navigate", url=result["url"])
                            
                            # Take screenshot of the page
                            if include_images:
                                page_screenshot = await browser.execute(action="screenshot")
                                if hasattr(page_screenshot, 'output') and page_screenshot.output:
                                    detailed_result["screenshot"] = page_screenshot.output
                            
                            # Get page text content
                            page_text = await browser.execute(action="get_text")
                            if hasattr(page_text, 'output') and page_text.output:
                                # Limit text content to avoid overwhelming results
                                text_content = page_text.output[:2000] + "..." if len(page_text.output) > 2000 else page_text.output
                                detailed_result["content"] = text_content
                        except Exception as e:
                            detailed_result["error"] = f"ページの取得中にエラーが発生しました: {str(e)}"
                    
                    detailed_results.append(detailed_result)
                
                # Prepare report
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                report = {
                    "query": query,
                    "timestamp": timestamp,
                    "num_results": len(detailed_results),
                    "search_screenshot": screenshot_base64,
                    "results": detailed_results,
                    "language": language,
                }
                
                return ToolResult(
                    output=f"「{query}」の検索レポートが生成されました。{len(detailed_results)}件の結果が含まれています。",
                    report=report,
                )
            
            except Exception as e:
                return ToolResult(error=f"検索レポートの生成に失敗しました: {str(e)}")

    def _parse_search_results(self, html_content: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Parse Google search results from HTML content.
        
        Args:
            html_content: HTML content of the search results page
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing search result information
        """
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find search result containers
            search_divs = soup.find_all('div', class_='g')
            
            for div in search_divs[:max_results]:
                result = {}
                
                # Extract title
                title_elem = div.find('h3')
                if title_elem:
                    result["title"] = title_elem.get_text()
                
                # Extract URL
                link_elem = div.find('a')
                if link_elem and 'href' in link_elem.attrs:
                    url = link_elem['href']
                    # Clean URL if it's a Google redirect
                    if url.startswith('/url?'):
                        url = url.split('&sa=')[0].replace('/url?q=', '')
                    result["url"] = url
                
                # Extract snippet
                snippet_elem = div.find('div', class_='VwiC3b')
                if snippet_elem:
                    result["snippet"] = snippet_elem.get_text()
                
                if result:
                    results.append(result)
                
                if len(results) >= max_results:
                    break
            
            # If we couldn't find results with the above selectors, try alternative selectors
            if not results:
                for div in soup.find_all('div', class_='tF2Cxc'):
                    result = {}
                    
                    # Extract title
                    title_elem = div.find('h3')
                    if title_elem:
                        result["title"] = title_elem.get_text()
                    
                    # Extract URL
                    link_elem = div.find('a')
                    if link_elem and 'href' in link_elem.attrs:
                        result["url"] = link_elem['href']
                    
                    # Extract snippet
                    snippet_elem = div.find('div', class_='IsZvec')
                    if snippet_elem:
                        result["snippet"] = snippet_elem.get_text()
                    
                    if result:
                        results.append(result)
                    
                    if len(results) >= max_results:
                        break
        
        except Exception as e:
            print(f"Error parsing search results: {e}")
        
        return results

    async def cleanup(self):
        """Clean up resources."""
        if self.browser_tool is not None:
            await self.browser_tool.cleanup()
            self.browser_tool = None

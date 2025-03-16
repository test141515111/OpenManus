#!/usr/bin/env python3
"""
Gradio wrapper for OpenManus Web UI - Simplified version
"""
import os
import sys
import gradio as gr
import time
import json
import tempfile
import base64
import asyncio
from pathlib import Path
import random

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)

from app.agent.manus import Manus
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.google_search import GoogleSearch
from app.tool.file_saver import FileSaver
from app.tool.terminate import Terminate

# Initialize Manus agent
async def initialize_manus():
    """Initialize the Manus agent with necessary tools."""
    try:
        # Create Manus agent
        agent = Manus()
        
        # Ensure browser tool is available
        browser_tool = agent.available_tools.get_tool("browser_use")
        if not browser_tool:
            browser_tool = BrowserUseTool()
            agent.available_tools.add_tool(browser_tool)
        
        # Ensure other tools are available
        if not agent.available_tools.get_tool("google_search"):
            agent.available_tools.add_tool(GoogleSearch())
        
        if not agent.available_tools.get_tool("file_saver"):
            agent.available_tools.add_tool(FileSaver())
        
        return agent
    except Exception as e:
        print(f"Error initializing Manus agent: {e}")
        return None

# Create screenshot directory
screenshot_dir = os.path.join(tempfile.gettempdir(), "openmanus_screenshots")
os.makedirs(screenshot_dir, exist_ok=True)

# Save base64-encoded screenshot to file
def save_base64_image(base64_data, prefix="screenshot"):
    """Save base64-encoded image to file and return the path."""
    try:
        image_data = base64.b64decode(base64_data)
        screenshot_path = os.path.join(screenshot_dir, f"{prefix}_{int(time.time())}.png")
        with open(screenshot_path, "wb") as f:
            f.write(image_data)
        return screenshot_path
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return None

# Sample screenshots for demonstration
def create_sample_screenshot(query):
    """Create a sample screenshot with the query text"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    
    # Create a blank image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to use a system font
    try:
        font = ImageFont.truetype("Arial", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw some text
    draw.text((50, 50), f"OpenManus ブラウザ", fill=(0, 0, 0), font=font)
    draw.text((50, 100), f"検索クエリ: {query}", fill=(0, 0, 0), font=font)
    
    # Draw a search box
    draw.rectangle([(50, 150), (750, 200)], outline=(0, 0, 0))
    draw.text((60, 165), query, fill=(0, 0, 0), font=font)
    
    # Draw some search results
    y_pos = 250
    for i in range(3):
        draw.text((50, y_pos), f"検索結果 {i+1}: {query}に関する情報", fill=(0, 0, 0), font=font)
        draw.text((50, y_pos+30), f"https://example.com/result{i+1}", fill=(0, 0, 255), font=font)
        draw.text((50, y_pos+60), f"{query}についての詳細な情報が含まれています。", fill=(100, 100, 100), font=font)
        y_pos += 100
    
    # Save the image
    screenshot_path = os.path.join(screenshot_dir, f"screenshot_{int(time.time())}.png")
    image.save(screenshot_path)
    
    return screenshot_path

# Create Gradio interface
def create_gradio_interface():
    with gr.Blocks(title="OpenManus ウェブUI") as demo:
        gr.Markdown("# OpenManus ウェブUI")
        gr.Markdown("ブラウザ機能を持つAIエージェント")
        
        with gr.Tabs() as tabs:
            with gr.Tab("メインページ"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## タスクを送信")
                        task_input = gr.Textbox(
                            label="OpenManusに何をさせたいですか？",
                            placeholder="タスクや質問をここに入力してください...",
                            lines=5
                        )
                        
                        sample_btn = gr.Button("サンプル: モテる方法を教えて", variant="secondary")
                        submit_btn = gr.Button("タスクを送信", variant="primary")
                        
                        gr.Markdown("## タスクの状態")
                        status_box = gr.Markdown("状態: 待機中\n\n現在のタスク: なし")
                        
                        gr.Markdown("## タスクの結果")
                        result_box = gr.Markdown("結果はありません")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("## ブラウザのスクリーンショット")
                        screenshot_box = gr.Image(label="スクリーンショット", type="filepath")
                        
                        gr.Markdown("## ブラウザの動画")
                        video_box = gr.Video(label="動画")
            
            with gr.Tab("ウェブ検索"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("## 検索クエリを送信")
                        search_input = gr.Textbox(
                            label="検索したい内容を入力してください",
                            placeholder="検索クエリを入力...",
                            lines=5
                        )
                        
                        with gr.Row():
                            result_count = gr.Slider(
                                label="結果の数 (1-5)",
                                minimum=1,
                                maximum=5,
                                value=3,
                                step=1
                            )
                            
                            language = gr.Dropdown(
                                label="言語",
                                choices=["日本語", "English"],
                                value="日本語"
                            )
                        
                        include_images = gr.Checkbox(label="画像を含める", value=True)
                        
                        gr.Markdown("※ 検索には数秒かかる場合があります。エラーが表示された場合は再度お試しください。")
                        search_btn = gr.Button("検索を実行", variant="primary")
                        
                        gr.Markdown("## 検索の状態")
                        search_status_box = gr.Markdown("状態: 待機中\n\n現在のクエリ: なし")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("## 検索結果")
                        search_result_box = gr.Markdown("検索結果はありません")
                        
                        gr.Markdown("## 検索スクリーンショット")
                        search_screenshot_box = gr.Image(label="スクリーンショット", type="filepath")
        
        # Sample button functionality
        def set_sample_text():
            return "モテる方法を教えて"
        
        sample_btn.click(fn=set_sample_text, outputs=task_input)
        
        # Task submission functionality
        async def process_task(task_text):
            if not task_text or task_text.strip() == "":
                return (
                    "状態: エラー\n\n現在のタスク: なし\n\n**エラー**: タスクが空です。",
                    "タスクを入力してください。",
                    None
                )
            
            # Update status
            status = f"状態: 実行中\n\n現在のタスク: {task_text}"
            
            try:
                # Initialize Manus agent
                agent = await initialize_manus()
                if not agent:
                    return (
                        f"状態: エラー\n\n現在のタスク: {task_text}\n\n**エラー**: Manusエージェントの初期化に失敗しました。",
                        "Manusエージェントの初期化に失敗しました。",
                        None
                    )
                
                # Execute task
                result = await agent.run(task_text)
                
                # Get screenshots from browser tool
                screenshot_path = None
                browser_tool = agent.available_tools.get_tool("browser_use")
                if browser_tool:
                    # Execute screenshot action
                    screenshot_result = await browser_tool.execute(action="screenshot")
                    if screenshot_result and hasattr(screenshot_result, "system") and screenshot_result.system:
                        screenshot_path = save_base64_image(screenshot_result.system)
                
                # Update status
                status = f"状態: 完了\n\n現在のタスク: {task_text}"
                
                return status, result, screenshot_path
            except Exception as e:
                error_message = f"エラー: {str(e)}"
                print(f"Error processing task: {e}")
                return (
                    f"状態: エラー\n\n現在のタスク: {task_text}\n\n**エラー**: {error_message}",
                    error_message,
                    None
                )
        
        # Convert synchronous function to asynchronous for Gradio
        def submit_task(task_text):
            return asyncio.run(process_task(task_text))
        
        submit_btn.click(
            fn=submit_task, 
            inputs=task_input, 
            outputs=[status_box, result_box, screenshot_box]
        )
        
        # Search functionality
        async def process_search(query, count, lang, images):
            if not query or query.strip() == "":
                return (
                    "状態: エラー\n\n現在のクエリ: なし\n\n**エラー**: 検索クエリが空です。",
                    "検索クエリを入力してください。",
                    None
                )
            
            # Update status
            status = f"状態: 検索中\n\n現在のクエリ: {query}"
            
            try:
                # Initialize Manus agent
                agent = await initialize_manus()
                if not agent:
                    return (
                        f"状態: エラー\n\n現在のクエリ: {query}\n\n**エラー**: Manusエージェントの初期化に失敗しました。",
                        "Manusエージェントの初期化に失敗しました。",
                        None
                    )
                
                # Get Google search tool
                search_tool = agent.available_tools.get_tool("google_search")
                if not search_tool:
                    search_tool = GoogleSearch()
                    agent.available_tools.add_tool(search_tool)
                
                # Execute search
                links = await search_tool.execute(query=query, num_results=int(count))
                
                # Format language and images for display
                language_str = "日本語" if lang == "日本語" else "英語"
                images_str = "含む" if images else "含まない"
                
                # Format search results
                results = f"""
                # 検索結果: {query}
                
                **検索設定**: 結果数 {count}、言語: {language_str}、画像: {images_str}
                
                ## 検索結果
                """
                
                # Add links to results
                for i, link in enumerate(links):
                    results += f"""
                {i+1}. [{link}]({link})
                """
                
                # Get screenshot from browser tool
                screenshot_path = None
                browser_tool = agent.available_tools.get_tool("browser_use")
                if browser_tool:
                    # Navigate to first search result if available
                    if links:
                        await browser_tool.execute(action="navigate", url=links[0])
                        # Take screenshot
                        screenshot_result = await browser_tool.execute(action="screenshot")
                        if screenshot_result and hasattr(screenshot_result, "system") and screenshot_result.system:
                            screenshot_path = save_base64_image(screenshot_result.system, prefix="search")
                
                # Update status
                status = f"状態: 完了\n\n現在のクエリ: {query}"
                
                return status, results, screenshot_path
            except Exception as e:
                error_message = f"エラー: {str(e)}"
                print(f"Error processing search: {e}")
                return (
                    f"状態: エラー\n\n現在のクエリ: {query}\n\n**エラー**: {error_message}",
                    error_message,
                    None
                )
        
        # Convert synchronous function to asynchronous for Gradio
        def perform_search(query, count, lang, images):
            return asyncio.run(process_search(query, count, lang, images))
        
        search_btn.click(
            fn=perform_search, 
            inputs=[search_input, result_count, language, include_images], 
            outputs=[search_status_box, search_result_box, search_screenshot_box]
        )
        
        gr.Markdown("### 注意事項")
        gr.Markdown("* サーバーは15分間の非アクティブ後にスリープモードに入ります")
        gr.Markdown("* 新しいリクエストを受信すると、数秒以内に自動的に起動します")
    
    return demo

if __name__ == "__main__":
    # Create and launch the Gradio interface
    demo = create_gradio_interface()
    demo.launch(share=True, server_name="0.0.0.0")

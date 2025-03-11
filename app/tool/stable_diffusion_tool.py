import asyncio
import base64
import io
from typing import Optional, Dict, Any, List

import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
from pydantic import Field

from app.tool.base import BaseTool, ToolResult


class StableDiffusionTool(BaseTool):
    """Tool for generating images using Stable Diffusion."""

    name: str = "stable_diffusion"
    description: str = """Generate images using Stable Diffusion AI model.
Use this tool when you need to create images based on text descriptions (prompts).
The tool accepts a text prompt and optional parameters to control the image generation process.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the image to generate",
            },
            "negative_prompt": {
                "type": "string",
                "description": "Text describing what you don't want in the image",
            },
            "num_images": {
                "type": "integer",
                "description": "Number of images to generate (1-4)",
            },
            "width": {
                "type": "integer",
                "description": "Width of the generated image (multiple of 8)",
            },
            "height": {
                "type": "integer",
                "description": "Height of the generated image (multiple of 8)",
            },
            "steps": {
                "type": "integer",
                "description": "Number of denoising steps (higher = better quality but slower)",
            },
            "guidance_scale": {
                "type": "number",
                "description": "How closely to follow the prompt (higher = more faithful)",
            },
            "seed": {
                "type": "integer",
                "description": "Random seed for reproducible results",
            },
        },
        "required": ["prompt"],
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    pipeline: Optional[StableDiffusionPipeline] = Field(default=None, exclude=True)
    model_id: str = Field(default="runwayml/stable-diffusion-v1-5")
    device: str = Field(default="cuda" if torch.cuda.is_available() else "cpu")

    async def _ensure_pipeline_initialized(self) -> StableDiffusionPipeline:
        """Ensure the Stable Diffusion pipeline is initialized."""
        if self.pipeline is None:
            # Initialize pipeline in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.pipeline = await loop.run_in_executor(
                None,
                lambda: StableDiffusionPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                ).to(self.device),
            )
        return self.pipeline

    async def execute(
        self,
        prompt: str,
        negative_prompt: Optional[str] = "",
        num_images: Optional[int] = 1,
        width: Optional[int] = 512,
        height: Optional[int] = 512,
        steps: Optional[int] = 30,
        guidance_scale: Optional[float] = 7.5,
        seed: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Generate images using Stable Diffusion.

        Args:
            prompt: Text description of the image to generate
            negative_prompt: Text describing what you don't want in the image
            num_images: Number of images to generate (1-4)
            width: Width of the generated image (multiple of 8)
            height: Height of the generated image (multiple of 8)
            steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            seed: Random seed for reproducible results
            **kwargs: Additional arguments

        Returns:
            ToolResult with the generated images as base64 strings
        """
        async with self.lock:
            try:
                # Validate parameters
                if num_images < 1 or num_images > 4:
                    return ToolResult(error="Number of images must be between 1 and 4")
                
                if width % 8 != 0 or height % 8 != 0:
                    return ToolResult(error="Width and height must be multiples of 8")
                
                if width * height > 1024 * 1024:
                    return ToolResult(error="Image dimensions too large. Maximum size is 1024x1024")
                
                # Initialize pipeline
                pipeline = await self._ensure_pipeline_initialized()
                
                # Set random seed if provided
                generator = None
                if seed is not None:
                    generator = torch.Generator(device=self.device).manual_seed(seed)
                
                # Generate images in a separate thread to avoid blocking
                loop = asyncio.get_event_loop()
                images = await loop.run_in_executor(
                    None,
                    lambda: pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_images_per_prompt=num_images,
                        width=width,
                        height=height,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    ).images,
                )
                
                # Convert images to base64
                base64_images = []
                for img in images:
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    base64_images.append(img_str)
                
                return ToolResult(
                    output=f"Generated {len(base64_images)} image(s) with prompt: {prompt}",
                    images=base64_images,
                )
            
            except Exception as e:
                return ToolResult(error=f"Image generation failed: {str(e)}")

    async def cleanup(self):
        """Clean up resources."""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        if self.pipeline is not None:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()

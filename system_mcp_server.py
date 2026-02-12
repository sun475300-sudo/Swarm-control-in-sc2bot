import asyncio
import os
import cv2
import base64
from mcp.server.fastmcp import FastMCP

# Create an MCP server for System Controls (Camera, Screenshot, etc.)
mcp = FastMCP("JARVIS-System-Manager")

@mcp.tool()
async def capture_webcam() -> str:
    """Captures a frame from the primary webcam and returns it as a base64 encoded string."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Error: Could not open webcam."
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return "Error: Could not read frame from webcam."
    
    # Encode as JPG
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    
    return f"data:image/jpeg;base64,{jpg_as_text}"

@mcp.tool()
async def capture_screenshot() -> str:
    """Captures a screenshot of the primary monitor and returns it as a base64 encoded string."""
    import pyautogui
    from io import BytesIO
    from PIL import Image
    
    screenshot = pyautogui.screenshot()
    buffered = BytesIO()
    screenshot.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return f"data:image/jpeg;base64,{img_str}"

if __name__ == "__main__":
    mcp.run()

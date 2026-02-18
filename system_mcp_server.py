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

@mcp.tool()
async def check_internet_speed() -> str:
    """인터넷 속도를 측정합니다 (다운로드/업로드/핑). 측정에 30초~1분 정도 소요됩니다."""
    import speedtest

    def _run_speedtest():
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000  # Mbps
        ping = st.results.ping
        server = st.results.server

        return (
            f"🌐 인터넷 속도 측정 결과\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 다운로드: {download:.1f} Mbps\n"
            f"📤 업로드: {upload:.1f} Mbps\n"
            f"📡 핑: {ping:.1f} ms\n"
            f"🖥️ 서버: {server['sponsor']} ({server['name']})\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_speedtest)
    return result


if __name__ == "__main__":
    mcp.run()

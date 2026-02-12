#!/usr/bin/env python3
"""
Mock VisionFive 2 Server - Simulates GPIO and Camera for Development

This server simulates the VisionFive 2 SBC (Single Board Computer) functionality
for local development without requiring the actual hardware.

Features:
- GPIO pin control simulation
- Camera capture simulation (returns test images)
- HTTP API compatible with real VisionFive server
"""

import asyncio
import base64
from aiohttp import web
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated GPIO state
gpio_state = {}

def generate_test_image(width=640, height=480):
    """
    Generate a test image with timestamp and random data.
    
    Returns:
        Base64 encoded JPEG image
    """
    # Create a test image
    img = Image.new('RGB', (width, height), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    
    # Add text
    text = f"Mock Camera Feed\\nTimestamp: {asyncio.get_event_loop().time():.2f}\\nRandom: {random.randint(1000, 9999)}"
    d.text((10, 10), text, fill=(255, 255, 0))
    
    # Add random noise pattern
    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        d.ellipse([x, y, x+5, y+5], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

async def handle_gpio_set(request):
    """
    Set GPIO pin state.
    
    POST /gpio/set
    Body: {"pin": 17, "value": 1}
    """
    try:
        data = await request.json()
        pin = data.get('pin')
        value = data.get('value')
        
        if pin is None or value is None:
            return web.json_response({'error': 'Missing pin or value'}, status=400)
        
        gpio_state[pin] = value
        logger.info(f"GPIO Pin {pin} set to {value}")
        
        return web.json_response({'pin': pin, 'value': value, 'status': 'success'})
    except Exception as e:
        logger.error(f"GPIO set error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def handle_gpio_get(request):
    """
    Get GPIO pin state.
    
    GET /gpio/get?pin=17
    """
    try:
        pin = int(request.query.get('pin', 0))
        value = gpio_state.get(pin, 0)
        
        logger.info(f"GPIO Pin {pin} read: {value}")
        return web.json_response({'pin': pin, 'value': value})
    except Exception as e:
        logger.error(f"GPIO get error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def handle_camera_capture(request):
    """
    Capture image from camera.
    
    GET /camera/capture
    Returns: {"image": "base64_encoded_jpeg"}
    """
    try:
        logger.info("Camera capture requested")
        img_b64 = generate_test_image()
        return web.json_response({'image': img_b64})
    except Exception as e:
        logger.error(f"Camera capture error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({
        'status': 'healthy',
        'device': 'Mock VisionFive 2',
        'gpio_pins': len(gpio_state),
        'camera': 'simulated'
    })

def main():
    """Start the mock VisionFive server."""
    app = web.Application()
    
    # Register routes
    app.router.add_post('/gpio/set', handle_gpio_set)
    app.router.add_get('/gpio/get', handle_gpio_get)
    app.router.add_get('/camera/capture', handle_camera_capture)
    app.router.add_get('/health', handle_health)
    
    # Start server
    port = 8888
    logger.info(f"🚀 Mock VisionFive 2 Server starting on port {port}")
    logger.info("Endpoints:")
    logger.info("  POST /gpio/set - Set GPIO pin")
    logger.info("  GET  /gpio/get?pin=X - Get GPIO pin state")
    logger.info("  GET  /camera/capture - Capture camera image")
    logger.info("  GET  /health - Health check")
    
    web.run_app(app, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()

import ast
import logging
import os
import subprocess
import tempfile
from mcp.server.fastmcp import FastMCP

try:
    import pyautogui
except ImportError:
    pyautogui = None

logger = logging.getLogger(__name__)

# ── Security: Command whitelist/blocklist ──
_ALLOWED_COMMANDS = {
    "git", "dir", "ls", "type", "cat", "echo", "npm", "npx", "pip", "python",
    "node", "docker", "kubectl", "where", "which", "whoami", "hostname",
    "ipconfig", "systeminfo", "tasklist", "netstat", "ping", "nslookup",
    "Get-ChildItem", "Get-Content", "Get-Process", "Get-Service",
    "Test-Connection", "Test-NetConnection",
}

_BLOCKED_PATTERNS = [
    "rm -rf", "Remove-Item", "del /", "rmdir", "format ", "diskpart",
    "shutdown", "restart", "Stop-Computer", "Restart-Computer",
    "reg delete", "reg add", "regedit",
    "net user", "net localgroup",
    "Invoke-WebRequest", "Invoke-Expression", "iex ",
    "curl ", "wget ",  # Prevent data exfiltration
    "certutil",  # Often used in attacks
    "powershell -enc", "powershell -e ",  # Encoded commands
]

def _is_command_allowed(command: str) -> tuple[bool, str]:
    """Check if a terminal command is allowed."""
    cmd_lower = command.strip().lower()

    # Check blocklist first
    for pattern in _BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            return False, f"Blocked command pattern: '{pattern}'"

    # Extract the base command (first word)
    base_cmd = command.strip().split()[0] if command.strip() else ""
    # Remove path prefixes
    base_cmd = base_cmd.replace("\\", "/").split("/")[-1]
    # Remove extension
    if "." in base_cmd:
        base_cmd = base_cmd.rsplit(".", 1)[0]

    if base_cmd.lower() not in {c.lower() for c in _ALLOWED_COMMANDS}:
        return False, f"Command '{base_cmd}' is not in the allowed list"

    return True, "OK"

# Create the MCP server for Agentic Computer Use & Terminal execution
mcp = FastMCP("JARVIS-Agentic-Core")

@mcp.tool()
async def execute_terminal_command(command: str, timeout: int = 15) -> str:
    """
    Executes a shell command (PowerShell default on Windows).
    Only allowed commands can be executed. Dangerous operations are blocked.
    """
    # Security: Check command whitelist
    allowed, reason = _is_command_allowed(command)
    if not allowed:
        logger.warning(f"[SECURITY] Blocked command: {command!r} - {reason}")
        return f"Command blocked for security: {reason}"

    # Limit timeout to prevent long-running commands
    timeout = min(timeout, 30)

    try:
        # Use powershell on Windows to allow robust scripting
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        stdout_text = result.stdout.strip()
        stderr_text = result.stderr.strip()
        
        out = []
        if stdout_text:
            out.append(f"[STDOUT]\n{stdout_text}")
        if stderr_text:
            out.append(f"[STDERR]\n{stderr_text}")
        
        if result.returncode == 0:
            if not out:
                return "Command executed successfully with no output."
            return "\n\n".join(out)
        else:
            out.insert(0, f"Command failed with return code {result.returncode}")
            return "\n\n".join(out)
            
    except subprocess.TimeoutExpired:
        logger.warning(f"명령 타임아웃 ({timeout}s): {command}")
        return f"Warning: Command '{command}' timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"명령 실행 오류: {command!r} → {e}")
        return f"Error executing command: {e}"

# ── Security: Python code sandbox ──
_ALLOWED_PYTHON_IMPORTS = {
    "math", "datetime", "json", "statistics", "re", "collections",
    "itertools", "functools", "decimal", "fractions", "random",
    "string", "textwrap", "csv", "io", "pprint", "typing",
    "dataclasses", "enum", "copy", "operator", "bisect", "heapq",
}

_BLOCKED_PYTHON_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "socket", "http",
    "urllib", "requests", "pathlib", "glob", "tempfile",
    "ctypes", "importlib", "code", "compile", "exec",
    "pickle", "shelve", "marshal", "builtins",
    "signal", "threading", "multiprocessing",
}

def _validate_python_code(code: str) -> tuple[bool, str]:
    """Validate Python code for dangerous imports and operations."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in _BLOCKED_PYTHON_IMPORTS:
                    return False, f"Import '{alias.name}' is blocked for security"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module in _BLOCKED_PYTHON_IMPORTS:
                    return False, f"Import from '{node.module}' is blocked for security"
        elif isinstance(node, ast.Call):
            # Block eval(), exec(), compile(), __import__()
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile", "__import__"):
                return False, f"Built-in '{func.id}()' is blocked for security"
            # Block getattr(__builtins__, ...) style bypass
            if isinstance(func, ast.Name) and func.id == "getattr":
                if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in ("__builtins__", "builtins"):
                    return False, f"getattr() on '{node.args[0].id}' is blocked for security"
        elif isinstance(node, ast.Attribute):
            # Block dunder attribute access (sandbox bypass vectors)
            _BLOCKED_ATTRS = {
                "__import__", "__builtins__", "__class__", "__subclasses__",
                "__globals__", "__code__", "__getattribute__", "__bases__",
                "__mro__", "__dict__",
            }
            if node.attr in _BLOCKED_ATTRS:
                return False, f"Attribute access '{node.attr}' is blocked for security"

    return True, "OK"


@mcp.tool()
async def execute_python_code(code: str) -> str:
    """
    Executes a Python script in a sandboxed environment.
    Only safe imports (math, datetime, json, etc.) are allowed.
    Blocked: os, subprocess, socket, sys, shutil, etc.
    """
    # Security: Validate code
    valid, reason = _validate_python_code(code)
    if not valid:
        logger.warning(f"[SECURITY] Blocked Python code: {reason}")
        return f"Code blocked for security: {reason}"

    try:
        # Save code to a temporary file, then run it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
            
        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            stdout_text = result.stdout.strip()
            stderr_text = result.stderr.strip()
            
            out = []
            if stdout_text:
                out.append(f"[STDOUT]\n{stdout_text}")
            if stderr_text:
                out.append(f"[STDERR]\n{stderr_text}")
            
            if result.returncode == 0:
                if not out:
                    return "Python code executed successfully with no output."
                return "\n\n".join(out)
            else:
                out.insert(0, f"Python execution failed with return code {result.returncode}")
                return "\n\n".join(out)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        return f"Error executing Python code: {e}"

# ── Security: File path validation ──
_BLOCKED_FILE_PATTERNS = [
    ".env", "credentials", "secret", ".git/config",
    "id_rsa", "id_ed25519", ".ssh/", "token",
    ".npmrc", ".pypirc",
]
_MAX_READ_SIZE = 1 * 1024 * 1024   # 1MB
_MAX_WRITE_SIZE = 10 * 1024 * 1024  # 10MB

def _is_path_safe(path: str) -> tuple[bool, str]:
    """Check if file path is safe to access."""
    path_lower = path.lower().replace("\\", "/")
    for pattern in _BLOCKED_FILE_PATTERNS:
        if pattern in path_lower:
            return False, f"Access to '{pattern}' files is blocked"
    return True, "OK"


@mcp.tool()
async def computer_use_mouse_move(x: int, y: int, duration: float = 0.5) -> str:
    """Moves the mouse to the specified (x, y) coordinates on the screen."""
    if pyautogui is None:
        return "Error: pyautogui module is not installed. Install with `pip install pyautogui`."
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return f"Mouse successfully moved to ({x}, {y})."
    except Exception as e:
        return f"Failed to move mouse: {e}"

@mcp.tool()
async def computer_use_mouse_click(button: str = "left", clicks: int = 1) -> str:
    """Clicks the mouse at the current position. button can be 'left', 'right', or 'middle'."""
    if pyautogui is None:
        return "Error: pyautogui module is not installed."
    try:
        if button not in ["left", "right", "middle"]:
            return "Error: invalid button name. Choose from 'left', 'right', 'middle'."
        
        pyautogui.click(button=button, clicks=clicks)
        return f"{button.capitalize()} mouse button clicked {clicks} time(s)."
    except Exception as e:
        return f"Failed to click mouse: {e}"

@mcp.tool()
async def computer_use_keyboard_type(text: str, interval: float = 0.05) -> str:
    """Types the given text on the keyboard."""
    if pyautogui is None:
        return "Error: pyautogui module is not installed."
    try:
        pyautogui.write(text, interval=interval)
        return f"Successfully typed text (length: {len(text)})."
    except Exception as e:
        return f"Failed to type text: {e}"

@mcp.tool()
async def computer_use_keyboard_press(keys_comma_separated: str) -> str:
    """
    Presses a combination of keys. Example: "ctrl,c", "alt,tab", "enter"
    """
    if pyautogui is None:
        return "Error: pyautogui module is not installed."
    try:
        keys = [k.strip() for k in keys_comma_separated.split(",")]
        # Execute hotkey
        pyautogui.hotkey(*keys)
        return f"Successfully pressed: {keys_comma_separated}"
    except Exception as e:
        return f"Failed to press keys: {e}"

@mcp.tool()
async def read_file(path: str) -> str:
    """Reads the contents of a file."""
    safe, reason = _is_path_safe(path)
    if not safe:
        return f"Access denied: {reason}"
    try:
        if os.path.exists(path) and os.path.getsize(path) > _MAX_READ_SIZE:
            return f"File too large (>{_MAX_READ_SIZE // 1024 // 1024}MB). Use a text editor."
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {e}"

@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Overwrites the contents of a file with 'content'."""
    safe, reason = _is_path_safe(path)
    if not safe:
        return f"Access denied: {reason}"
    if len(content.encode('utf-8')) > _MAX_WRITE_SIZE:
        return f"Content too large (>{_MAX_WRITE_SIZE // 1024 // 1024}MB)"
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to file {path}."
    except Exception as e:
        return f"Error writing to file {path}: {e}"

@mcp.tool()
async def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replaces first occurrence of 'old_text' with 'new_text' in the specified file."""
    safe, reason = _is_path_safe(path)
    if not safe:
        return f"Access denied: {reason}"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if old_text not in content:
            return f"Error: 'old_text' not found in {path}"
            
        new_content = content.replace(old_text, new_text, 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"Successfully edited file {path}."
    except Exception as e:
        return f"Error editing file {path}: {e}"

@mcp.tool()
async def list_directory(path: str = ".") -> str:
    """Lists the contents of the specified directory."""
    try:
        items = os.listdir(path)
        output = [f"Contents of directory: {path}"]
        for item in items:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                output.append(f"[DIR]  {item}")
            else:
                size = os.path.getsize(item_path)
                output.append(f"[FILE] {item} ({size} bytes)")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing directory {path}: {e}"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        logger.info("Starting JARVIS Agentic MCP Server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("JARVIS Agentic MCP Server terminating...")

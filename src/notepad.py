"""Notepad window management functions."""
import time
import pyautogui
import pyperclip
import pygetwindow as gw
import requests
from pathlib import Path
from botcity.core import DesktopBot

from .icon_detector import find_icon, set_cache, invalidate_cache
from .config import API_URL, SPACING


# ============================================================================
# Helper Functions
# ============================================================================

def _wait(delay: float = SPACING):
    """Wait for the default spacing time."""
    time.sleep(delay)


def _activate_and_click_center(window):
    """Activate a window and click its center."""
    window.activate()
    _wait()
    center_x = window.left + window.width // 2
    center_y = window.top + window.height // 2
    pyautogui.click(center_x, center_y)
    _wait()


def _wait_for_dialog(title: str, timeout: float, wait_for_appear: bool = True) -> bool:
    """Wait for a dialog window to appear or close.
    
    Args:
        title: Dialog window title
        timeout: Maximum time to wait in seconds
        wait_for_appear: If True, wait for dialog to appear; if False, wait for it to close
    
    Returns:
        True if dialog appeared (when wait_for_appear=True), False otherwise
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        dialogs = gw.getWindowsWithTitle(title)
        found = bool(dialogs)
        
        if wait_for_appear and found:
            dialogs[0].activate()
            _wait()
            return True
        elif not wait_for_appear and not found:
            return True
        
        _wait()
    
    return False if wait_for_appear else True

# ============================================================================
# Window Management
# ============================================================================

def get_notepad_windows():
    all_windows = gw.getWindowsWithTitle("Notepad")
    notepad_windows = []
    
    for window in all_windows:
        title = window.title.lower()
        if title == "notepad" or title.endswith(" - notepad"):
            notepad_windows.append(window)
    
    return notepad_windows
# ============================================================================
# Window Closing
# ============================================================================

def close_notepad() -> bool:
    """Close all Notepad windows. Returns True if all windows were closed."""
    active_windows = get_notepad_windows()
    if not active_windows:
        return True
    
    # Close all visible windows
    for window in active_windows:
        if window.visible:
            window.close()
    
    _wait(0.5)
    
    # Check if any windows remain visible
    remaining = get_notepad_windows()
    return not remaining or not any(win.visible for win in remaining)


# ============================================================================
# Icon Detection & Launching
# ============================================================================

def launch_notepad(bot: DesktopBot, template_labels: list[str]) -> bool:
    """Launch Notepad by finding and clicking the icon."""
    # Try once with cache 
    coords = find_icon(bot, template_labels, use_cache=True)
    if coords:
        if _verify_notepad_launched(coords):
            return True
        # if not launched, invalidate the cache
        invalidate_cache()
    
    # Try 3 times without cache (fresh search)
    for attempt in range(3):
        coords = find_icon(bot, template_labels, use_cache=False)
        if coords:
            if _verify_notepad_launched(coords):
                return True
        _wait()
    
    return False


def _verify_notepad_launched(coords: tuple[int, int] | None) -> bool:
    """Verify that Notepad launched successfully."""
    timeout = time.time() + 5
    while time.time() < timeout:
        active_windows = get_notepad_windows()
        if any(win.visible for win in active_windows):
            if coords:
                set_cache(coords)
            _wait()
            return True
        _wait()
    return False


# ============================================================================
# Content Writing
# ============================================================================

def _prepare_notepad_window():
    """Prepare Notepad window by activating and clicking center."""
    active_windows = get_notepad_windows()
    if active_windows:
        _activate_and_click_center(active_windows[0])


def _paste_content(content: str):
    """Paste content into Notepad using clipboard."""
    pyperclip.copy(content)
    _wait()
    # Select all content, delete it, and paste the new content
    pyautogui.hotkey('ctrl', 'a')
    _wait()
    pyautogui.press('delete')
    _wait()
    pyautogui.hotkey('ctrl', 'v')
    _wait()


def _save_file(filepath: str) -> bool:
    """Save file via Save As dialog. Returns True if successful."""
    pyautogui.hotkey('ctrl', 's')
    _wait()
    
    if not _wait_for_dialog("Save As", 3, wait_for_appear=True):
        return False
    
    pyautogui.hotkey('ctrl', 'a')
    _wait()
    pyperclip.copy(filepath)
    _wait()
    pyautogui.hotkey('ctrl', 'v')
    _wait()
    pyautogui.press('enter')
    _wait()
    
    # Handle confirmation dialog if file exists
    confirm_window = gw.getWindowsWithTitle("Confirm Save As")
    if confirm_window:
        confirm_window[0].activate()
        _wait()
        pyautogui.press('y')
        _wait()
    
    # Wait for dialog to close
    _wait_for_dialog("Save As", 2.0, wait_for_appear=False)
    return True


def write_post_to_notepad(post: dict, project_path: Path):
    """Write post content to Notepad and save it."""
    # Wait for any existing Save As dialogs to close before starting
    _wait_for_dialog("Save As", 2.0, wait_for_appear=False)
    
    _prepare_notepad_window()
    pyautogui.hotkey('ctrl', 'n')
    _wait()
    _prepare_notepad_window()
    
    content = f"Title: {post['title']}\n\n{post['body']}"
    _paste_content(content)
    
    filename = f"post_{post['id']}.txt"
    filepath = str(project_path / filename)
    
    if not _save_file(filepath):
        print(f"Warning: Save As dialog not found for post {post['id']}")
        return
    

    _prepare_notepad_window()
    
    # Close the tab/document
    pyautogui.hotkey('ctrl', 'w')
    _wait()
    
    close_notepad()

# API fetching
def fetch_posts() -> list[dict] | None:
    """Fetch posts from the API."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: API is unavailable. {e}")
        return None

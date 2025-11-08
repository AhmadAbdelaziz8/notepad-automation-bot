"""Notepad window management functions."""
import time
import pyautogui
import pyperclip
import pygetwindow as gw
import requests
from pathlib import Path
from botcity.core import DesktopBot

from .icon_detector import icon_cache, get_icon_coordinates, find_icon
from .config import MATCHING_THRESHOLD, FIND_WAIT_TIME, API_URL, PROJECT_PATH


def get_notepad_windows():
    all_windows = gw.getWindowsWithTitle("Notepad")
    notepad_windows = []
    
    for window in all_windows:
        title = window.title.lower()
        if title == "notepad" or title.endswith(" - notepad"):
            notepad_windows.append(window)
    
    return notepad_windows


def _is_valid_notepad(window) -> bool:
    """Check if window is a valid Notepad window."""
    title = window.title.lower()
    return "cursor" not in title and "code" not in title


def close_existing_notepad():
    """Close all existing Notepad windows."""
    active_windows = get_notepad_windows()
    if not active_windows:
        return
    
    for window in active_windows:
        if window.visible and _is_valid_notepad(window):
            window.close()
            time.sleep(0.5)
            try:
                pyautogui.press('n')
                time.sleep(0.3)
            except:
                pass
    
    time.sleep(0.5)
    
    remaining_windows = get_notepad_windows()
    if remaining_windows:
        for window in remaining_windows:
            if window.visible and _is_valid_notepad(window):
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.3)
                pyautogui.press('n')
                time.sleep(0.3)


def close_notepad_fully() -> bool:
    """Close Notepad windows with verification."""
    active_windows = get_notepad_windows()
    if not active_windows:
        return True
    
    for window in active_windows:
        if window.visible and _is_valid_notepad(window):
            try:
                window.close()
                time.sleep(0.5)
            except:
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.5)
    
    timeout = time.time() + 5
    while time.time() < timeout:
        remaining_windows = get_notepad_windows()
        if not remaining_windows or not any(win.visible for win in remaining_windows):
            time.sleep(0.5)
            return True
        time.sleep(0.2)
    
    remaining_windows = get_notepad_windows()
    if remaining_windows:
        for window in remaining_windows:
            if window.visible and _is_valid_notepad(window):
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.3)
                pyautogui.press('n')
                time.sleep(0.5)
        
        final_check = get_notepad_windows()
        if not final_check or not any(win.visible for win in final_check):
            return True
        return False
    
    return True


def fetch_posts() -> list[dict] | None:
    """Fetch posts from the API."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: API is unavailable. {e}")
        return None


def launch_notepad(bot: DesktopBot, template_labels: list[str]) -> bool:
    """Launch Notepad by finding and clicking the icon."""
    found_label = None
    
    for attempt in range(3):
        found_label = find_icon(bot, template_labels)
        if found_label:
            break
        time.sleep(1)
        
    if not found_label:
        return False
    
    clicked_coords = None
    used_cache = False
    
    if found_label in icon_cache:
        cached_x, cached_y = icon_cache[found_label]
        cached_x, cached_y = int(cached_x), int(cached_y)
        clicked_coords = (cached_x, cached_y)
        used_cache = True
        
        try:
            pyautogui.doubleClick(cached_x, cached_y)
            time.sleep(0.3)
        except:
            if found_label in icon_cache:
                del icon_cache[found_label]
            clicked_coords = None
            used_cache = False
    
    if not clicked_coords:
        clicked_coords = _click_icon(bot, found_label)
        if not clicked_coords:
            return False
    
    if _verify_notepad_launched(found_label, clicked_coords):
        return True
    
    if used_cache:
        return _retry_launch_without_cache(bot, template_labels, found_label)
    
    return False


def _click_icon(bot: DesktopBot, label: str) -> tuple[int, int] | None:
    """Click on an icon and return its coordinates."""
    thresholds = [MATCHING_THRESHOLD, MATCHING_THRESHOLD - 0.1]
    for threshold in thresholds:
        if bot.find(label=label, matching=threshold, waiting_time=FIND_WAIT_TIME):
            coords = get_icon_coordinates(label)
            if coords:
                pyautogui.doubleClick(coords[0], coords[1])
                return coords
            else:
                bot.double_click()
                return None
    return None


def _verify_notepad_launched(label: str, coords: tuple[int, int] | None) -> bool:
    """Verify that Notepad launched successfully."""
    timeout = time.time() + 5
    while time.time() < timeout:
        active_windows = get_notepad_windows()
        if any(win.visible for win in active_windows):
            if coords and label:
                icon_cache[label] = coords
            time.sleep(0.5)
            return True
        time.sleep(0.2)
    return False


def _retry_launch_without_cache(bot: DesktopBot, template_labels: list[str], old_label: str) -> bool:
    """Retry launching Notepad after cache invalidation."""
    if old_label in icon_cache:
        del icon_cache[old_label]
    
    found_label = find_icon(bot, template_labels, use_cache=False)
    if not found_label:
        return False
    
    clicked_coords = _click_icon(bot, found_label)
    if not clicked_coords:
        return False
    
    return _verify_notepad_launched(found_label, clicked_coords)


def write_post_to_notepad(post: dict, project_path: Path):
    """Write post content to Notepad and save it."""
    active_windows = get_notepad_windows()
    if active_windows:
        window = active_windows[0]
        window.activate()
        time.sleep(0.2)
        
        center_x = window.left + window.width // 2
        center_y = window.top + window.height // 2
        pyautogui.click(center_x, center_y)
        time.sleep(0.15)
    
    time.sleep(0.2)
    save_dialogs = gw.getWindowsWithTitle("Save As")
    if save_dialogs:
        timeout = time.time() + 2
        while time.time() < timeout and gw.getWindowsWithTitle("Save As"):
            time.sleep(0.1)
    
    pyautogui.hotkey('ctrl', 'n')
    time.sleep(0.4)
    
    active_windows = get_notepad_windows()
    if active_windows:
        window = active_windows[0]
        window.activate()
        time.sleep(0.15)
        center_x = window.left + window.width // 2
        center_y = window.top + window.height // 2
        pyautogui.click(center_x, center_y)
        time.sleep(0.15)
    
    content = f"Title: {post['title']}\n\n{post['body']}"
    pyperclip.copy(content)
    time.sleep(0.1)
    
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.15)
    pyautogui.press('delete')
    time.sleep(0.15)
    
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)
    
    pyautogui.hotkey('ctrl', 's')
    time.sleep(0.8)
    
    # Wait for Save As dialog to appear
    save_dialog_timeout = time.time() + 3
    save_dialog_found = False
    while time.time() < save_dialog_timeout:
        save_dialogs = gw.getWindowsWithTitle("Save As")
        if save_dialogs:
            save_dialog_found = True
            save_dialogs[0].activate()
            time.sleep(0.2)
            break
        time.sleep(0.1)
    
    if not save_dialog_found:
        print(f"Warning: Save As dialog not found for post {post['id']}")
        return
    
    # Navigate to the filename field (Alt+N or just click in the filename area)
    # First, clear any existing text in the filename field
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    
    filename = f"post_{post['id']}.txt"
    filepath = str(project_path / filename)
    
    # Use clipboard to paste the full path (more reliable than typing)
    pyperclip.copy(filepath)
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)
    pyautogui.press('enter')
    time.sleep(0.5)
    
    # Check for confirmation dialog (file already exists)
    confirm_window = gw.getWindowsWithTitle("Confirm Save As")
    if confirm_window:
        confirm_window[0].activate()
        time.sleep(0.1)
        pyautogui.press('y')
        time.sleep(0.3)
    
    # Wait for Save As dialog to close and return to Notepad
    save_dialog_timeout = time.time() + 2
    while time.time() < save_dialog_timeout:
        save_dialogs = gw.getWindowsWithTitle("Save As")
        if not save_dialogs:
            break
        time.sleep(0.1)
    
    # Ensure we're back in the Notepad window and it's focused
    active_windows = get_notepad_windows()
    if active_windows:
        window = active_windows[0]
        window.activate()
        time.sleep(0.2)
        
        # Click in the window to ensure focus
        center_x = window.left + window.width // 2
        center_y = window.top + window.height // 2
        pyautogui.click(center_x, center_y)
        time.sleep(0.15)
    
    # Close the tab/document with Ctrl+W (for tabbed Notepad)
    # If Ctrl+W doesn't work, we'll fall back to closing the window
    pyautogui.hotkey('ctrl', 'w')
    time.sleep(0.5)
    
    # Check if window still exists - if so, close it directly
    active_windows = get_notepad_windows()
    if active_windows:
        for window in active_windows:
            if window.visible:
                window.activate()
                time.sleep(0.1)
                # Try Alt+F4 as alternative
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.3)
                # If still open, force close
                if window.visible:
                    window.close()
                    time.sleep(0.2)
import cv2
import numpy as np
import pyautogui
import requests
import mss
import time
import pygetwindow as gw
from pathlib import Path
import pyperclip

# --- Constants ---
API_URL = "https://jsonplaceholder.typicode.com/posts"
RESOLUTION = (1920, 1080)
RETRY_LIMIT = 3
RETRY_DELAY_S = 1
MATCH_THRESHOLD = 0.8 # 80% confidence
PROJECT_DIR_NAME = "tjm-project"
PROJECT_PATH = Path.home() / "Desktop" / PROJECT_DIR_NAME

# NEW: Point to our template directory
TEMPLATE_DIR = Path("assets/templates")

# --- 1. Load All Templates ---
def load_templates(directory):
    """Loads all .png templates from a directory."""
    templates = []
    if not directory.is_dir():
        print(f"Error: Template directory not found at {directory}")
        return []
        
    for img_path in directory.glob("*.png"):
        template = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if template is not None:
            templates.append((img_path.name, template))
            print(f"Loaded template: {img_path.name}")
    return templates

# --- 2. The "Smarter" Grounding Function ---
def find_icon_with_multiple_templates(templates):
    """
    Locates an icon by trying a list of templates.
    Returns: (x, y) center coordinates or None if not found.
    """
    with mss.mss() as sct:
        # Capture the screen ONCE
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        screen = np.array(sct_img)
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

        best_match_score = 0.0
        best_match_loc = None
        best_match_dims = (0, 0)
        best_template_name = ""

        # Loop through every template we loaded
        for name, template in templates:
            
            # Handle alpha/transparency in the template
            if template.shape[2] == 4:
                mask = template[:, :, 3]
                template_bgr = template[:, :, :3]
            else:
                mask = None
                template_bgr = template
            
            template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            
            # Skip if template is too big
            if template_gray.shape[0] > screen_gray.shape[0] or template_gray.shape[1] > screen_gray.shape[1]:
                print(f"Skipping template {name}, it's larger than the screen.")
                continue

            w, h = template_gray.shape[::-1]

            # Perform the match
            res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            # Check if this match is the best one so far
            if max_val > best_match_score:
                best_match_score = max_val
                best_match_loc = max_loc
                best_match_dims = (w, h)
                best_template_name = name

        # AFTER checking all, see if our best match is good enough
        if best_match_score >= MATCH_THRESHOLD:
            w, h = best_match_dims
            center_x = best_match_loc[0] + w // 2
            center_y = best_match_loc[1] + h // 2
            print(f"Icon found! Best match: '{best_template_name}' (Confidence: {best_match_score:.2f})")
            return (center_x, center_y)
        
        return None # No match found

# --- 3. API & Setup ---
def fetch_posts():
    """Fetches post data from JSONPlaceholder."""
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: API is unavailable. {e}")
        return None

def setup_environment():
    """Creates the target directory on the desktop."""
    print(f"Ensuring project directory exists: {PROJECT_PATH}")
    PROJECT_PATH.mkdir(parents=True, exist_ok=True)

# --- 4. Main Automation Workflow ---
def get_notepad_windows():
    """Gets only actual Notepad windows, filtering out other applications."""
    all_windows = gw.getWindowsWithTitle("Notepad")
    notepad_windows = []
    
    for window in all_windows:
        title = window.title.lower()
        # Only include windows that are clearly Notepad windows
        # Notepad titles are typically: "Notepad", "Untitled - Notepad", or "filename.txt - Notepad"
        if title == "notepad" or title.endswith(" - notepad") or "notepad" in title:
            # Additional check: exclude windows that might be other apps
            # Cursor or other editors might have "notepad" in their title but not be Notepad
            if "cursor" not in title and "code" not in title and "editor" not in title:
                notepad_windows.append(window)
    
    return notepad_windows

def close_existing_notepad():
    """Closes any existing Notepad windows without saving."""
    active_windows = get_notepad_windows()
    if not active_windows:
        return
    
    print(f"Found {len(active_windows)} existing Notepad window(s). Closing...")
    for window in active_windows:
        if window.visible:
            # Verify it's actually Notepad before closing
            title = window.title.lower()
            if "cursor" in title or "code" in title:
                print(f"Skipping non-Notepad window: {window.title}")
                continue
                
            window.close()
            time.sleep(0.5)  # Wait for close dialog if it appears
            
            # Handle "Save changes?" dialog if it appears
            # Windows Notepad may show a dialog asking to save changes
            # Press 'n' to discard changes (don't save)
            try:
                # Check for dialog windows (common titles include "Notepad" with dialog)
                dialog_windows = get_notepad_windows()
                # If there's still a Notepad window visible, it might be a dialog
                # Send 'n' to discard changes
                pyautogui.press('n')
                time.sleep(0.3)
            except:
                pass  # If no dialog appears, continue
    
    # Wait a bit more to ensure all windows are closed
    time.sleep(0.5)
    
    # Final check - if any Notepad windows remain, try Alt+F4 as fallback
    remaining_windows = get_notepad_windows()
    if remaining_windows:
        for window in remaining_windows:
            if window.visible:
                title = window.title.lower()
                if "cursor" in title or "code" in title:
                    continue  # Skip non-Notepad windows
                    
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.3)
                pyautogui.press('n')  # Discard changes if dialog appears
                time.sleep(0.3)
    
    print("Existing Notepad windows closed.")

def close_notepad_fully():
    """Closes Notepad window and verifies it is fully closed."""
    print("Closing Notepad...")
    active_windows = get_notepad_windows()
    
    if not active_windows:
        print("No Notepad windows found to close.")
        return True
    
    # Close all Notepad windows
    for window in active_windows:
        if window.visible:
            try:
                # Verify it's actually Notepad before closing
                title = window.title.lower()
                if "cursor" in title or "code" in title:
                    print(f"Skipping non-Notepad window: {window.title}")
                    continue
                    
                window.close()
                time.sleep(0.5)
            except:
                # Fallback to Alt+F4 if close() fails, but only if it's actually Notepad
                title = window.title.lower()
                if "cursor" not in title and "code" not in title:
                    window.activate()
                    time.sleep(0.2)  # Brief pause before sending Alt+F4
                    pyautogui.hotkey('alt', 'f4')
                    time.sleep(0.5)
    
    # Verify closure with timeout
    timeout = time.time() + 5  # 5 second timeout
    while time.time() < timeout:
        remaining_windows = get_notepad_windows()
        if not remaining_windows or not any(win.visible for win in remaining_windows):
            print("Notepad successfully closed and verified.")
            time.sleep(0.5)  # Additional wait to ensure cleanup
            return True
        time.sleep(0.2)
    
    # If still open, try more aggressive closing (but only for actual Notepad)
    remaining_windows = get_notepad_windows()
    if remaining_windows:
        print("Warning: Notepad still open, trying aggressive close...")
        for window in remaining_windows:
            if window.visible:
                title = window.title.lower()
                if "cursor" in title or "code" in title:
                    continue  # Skip non-Notepad windows
                    
                window.activate()
                time.sleep(0.2)
                pyautogui.hotkey('alt', 'f4')
                time.sleep(0.3)
                # Handle any save dialog
                pyautogui.press('n')  # Don't save
                time.sleep(0.5)
        
        # Final verification
        final_check = get_notepad_windows()
        if not final_check or not any(win.visible for win in final_check):
            print("Notepad closed after aggressive attempt.")
            return True
        else:
            print("Error: Failed to close Notepad completely.")
            return False
    
    return True

def launch_and_validate_notepad(templates_list):
    """Finds, clicks, and validates Notepad launch."""
    icon_coords = None
    for attempt in range(RETRY_LIMIT):
        icon_coords = find_icon_with_multiple_templates(templates_list)
        if icon_coords:
            break
        print(f"Icon not found (Attempt {attempt + 1}/{RETRY_LIMIT}). Retrying...")
        time.sleep(RETRY_DELAY_S)
        
    if not icon_coords:
        print("Error: Icon not found after 3 attempts.")
        return False # Failed to find icon
        
    print(f"Double-clicking Notepad icon at {icon_coords}")
    pyautogui.doubleClick(icon_coords[0], icon_coords[1])
    
    # Validate launch (robustness check)
    timeout = time.time() + 5 # 5 second timeout
    while time.time() < timeout:
        # Check for "Untitled - Notepad" or just "Notepad"
        active_windows = get_notepad_windows()
        if any(win.visible for win in active_windows):
            print("Notepad successfully launched and validated.")
            time.sleep(1) # Give window time to fully open
            return True
        time.sleep(0.2)
        
    print("Error: Notepad window not detected after launch.")
    return False

def process_single_post(post, templates_list):
    """Main automation loop for a single post."""
    print(f"\nProcessing Post ID: {post['id']}")
    
    # Close any existing Notepad windows before launching a fresh one
    close_existing_notepad()
    
    if not launch_and_validate_notepad(templates_list):
        print(f"Skipping post {post['id']} due to launch failure.")
        return

    try:
        # Ensure Notepad window is active/focused
        active_windows = get_notepad_windows()
        if active_windows:
            window = active_windows[0]
            window.activate()
            time.sleep(0.5)
            
            # Click in the center of the text area to ensure focus
            # Get window center coordinates (accounting for menu bar)
            center_x = window.left + window.width // 2
            center_y = window.top + window.height // 2
            pyautogui.click(center_x, center_y)
            time.sleep(0.3)
        
        # Create a new file/tab to ensure we're working with a fresh document
        # This prevents writing to an existing tab
        pyautogui.hotkey('ctrl', 'n')
        time.sleep(0.5)  # Wait for new file/tab to be created
        
        # Clear any existing content (safety measure)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.press('delete')
        time.sleep(0.2)
        
        # Prepare content with proper formatting
        content = f"Title: {post['title']}\n\n{post['body']}"
        
        # Use clipboard to paste content instead of typing character by character
        # This prevents character loss that occurs when typing too fast
        pyperclip.copy(content)
        time.sleep(0.1)  # Brief pause to ensure clipboard is ready
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)  # Wait for paste to complete
        
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)
        
        filename = f"post_{post['id']}.txt"
        filepath = str(PROJECT_PATH / filename)
        pyautogui.write(filepath, interval=0.01)
        pyautogui.press('enter')
        time.sleep(0.5)
        
        # Handle "File Exists"
        confirm_window = gw.getWindowsWithTitle("Confirm Save As")
        if confirm_window:
            print("File exists. Overwriting.")
            pyautogui.press('y')
            time.sleep(0.5)

        # Close Notepad fully and verify closure
        if not close_notepad_fully():
            print(f"Warning: Notepad may not have closed completely for post {post['id']}")
        
        print(f"Successfully processed Post ID: {post['id']}")
        
    except Exception as e:
        print(f"An error occurred during post processing: {e}")

# --- 5. Main Execution ---
def main():
    setup_environment()
    
    all_templates = load_templates(TEMPLATE_DIR)
    if not all_templates:
        print("Exiting, no templates found. Check the 'assets/templates' folder.")
        return

    posts = fetch_posts()
    if not posts:
        print("Exiting due to API failure.")
        return

    print("Starting automation. Please do not move the mouse.")
    time.sleep(3)

    for post in posts[:10]:
        process_single_post(post, all_templates)

if __name__ == "__main__":
    main()
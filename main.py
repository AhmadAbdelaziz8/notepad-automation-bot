import time
import pyautogui
from botcity.core import DesktopBot

from src.icon_detector import register_templates

from src.notepad import (
    close_notepad,
    fetch_posts,
    launch_notepad,
    write_post_to_notepad,
)
from src.config import TEMPLATE_DIR, PROJECT_PATH, SPACING


def process_post(post: dict, bot: DesktopBot, template_labels: list[str]):
    """Process a single post: launch Notepad, write content, and close."""
    print(f"Processing Post ID: {post['id']}")

    close_notepad()
    
    if not launch_notepad(bot, template_labels):
        print(f"Skipping post {post['id']} due to launch failure.")
        return

    try:
        write_post_to_notepad(post, PROJECT_PATH)
        close_notepad()
    except Exception as e:
        print(f"Error processing post {post['id']}: {e}")


def main():
    """Main execution function."""

    # Minimize all windows
    pyautogui.hotkey('win', 'd')
    time.sleep(SPACING)

    # Ensure project directory exists
    PROJECT_PATH.mkdir(parents=True, exist_ok=True)


    # Initialize bot and register templates
    bot = DesktopBot()
    template_labels = [img_path.stem for img_path in TEMPLATE_DIR.glob("*.png")]
    if not template_labels or not register_templates(bot, TEMPLATE_DIR):
        print("Error: No templates found.")
        return

    # Fetch posts from API
    posts = fetch_posts()
    if not posts:
        print("Error: API failure.")
        return


    for post in posts[:10]:
        process_post(post, bot, template_labels)


if __name__ == "__main__":
    main()

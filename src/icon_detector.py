"""Template registration and icon finding."""
from pathlib import Path
import pyautogui
from botcity.core import DesktopBot

from .config import MATCHING_THRESHOLD, FIND_WAIT_TIME

# Icon cache for faster subsequent lookups / in case of the same coordinates
icon_cache: tuple[int, int] | None = None


def register_templates(bot: DesktopBot, directory: Path) -> bool:
    """Register all PNG templates from the given directory."""
    if not directory.is_dir():
        return False
    
    for img_path in directory.glob("*.png"):
        label = img_path.stem
        bot.add_image(label, str(img_path.resolve()))
    
    return True


def set_cache(coords: tuple[int, int]):
    """Set the cached icon coordinates."""
    global icon_cache
    icon_cache = coords


def invalidate_cache():
    """Clear the cached icon coordinates."""
    global icon_cache
    icon_cache = None


def find_icon(bot: DesktopBot, template_labels: list[str], use_cache: bool = True, click: bool = False) -> tuple[int, int] | None:
    """Find an icon from the given template labels and return coordinates.
    
    Args:
        bot: DesktopBot instance
        template_labels: List of template labels to search
        use_cache: Whether to use cached coordinates
        click: Whether to double-click the icon after finding it
    
    Returns:
        Tuple of (x, y) coordinates or None if not found
    """
    global icon_cache
    # Try to find the icon using the cache
    if use_cache and icon_cache:
        coords = icon_cache
        if click:
            x, y = coords
            pyautogui.doubleClick(x, y)
        return coords
    
    thresholds = [MATCHING_THRESHOLD, MATCHING_THRESHOLD - 0.1]
    for threshold in thresholds:
        for label in template_labels:
            if bot.find(label=label, matching=threshold, waiting_time=FIND_WAIT_TIME):
                # Get coordinates immediately after successful find
                coords = bot.get_element_coords(label, matching=threshold)
                
                if coords:
                    x, y = int(coords[0]), int(coords[1])
                    set_cache((x, y))
                    if click:
                        pyautogui.doubleClick(x, y)
                    return (x, y)
    
    return None


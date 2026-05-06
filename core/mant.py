import os
import re

import pyautogui

import core.state as state
import utils.constants as constants
from core.ocr import extract_number, extract_text
from core.recognizer import match_template, is_btn_active
from utils.screenshot import enhanced_screenshot
from utils.log import info, warning, debug
from utils.tools import drag_scroll, get_secs, sleep


ITEM_ASSET_ROOT = os.path.join("assets", "mant")
BUTTON_ASSETS = {
  "shop": os.path.join(ITEM_ASSET_ROOT, "shop.png"),
  "training_items": os.path.join(ITEM_ASSET_ROOT, "training_items.png"),
  "close_training_items": os.path.join(ITEM_ASSET_ROOT, "close_training_items.png"),
  "shop_checkbox": os.path.join(ITEM_ASSET_ROOT, "check_box.png"),
  "confirm_purchase": os.path.join(ITEM_ASSET_ROOT, "confirm.png"),
  "confirm_use": os.path.join(ITEM_ASSET_ROOT, "confirm_use.png"),
  "confirm_use2": os.path.join(ITEM_ASSET_ROOT, "confirm_use2.png"),
}
ITEM_PRIORITIES = {
    "empowering megaphone": 0,
    "vita 20": 0, "vita 40": 0, "vita 65": 0.1,
    "berry sweet cupcake": 0.5, "plain cupcake": 0,
    "glow sticks": 0.1, "royal kale juice": 0,
    "good-luck charm": 0, "rich hand cream": 0.2, "miracle cure": 2,
    "master cleat hammer": 0, "artisan cleat hammer": 0,
    "stamina scroll": 0, "speed scroll": 0, "power scroll": 0, "guts scroll": 0, "wit scroll": 0,
    "stamina manual": 0, "speed manual": 0, "power manual": 0, "guts manual": 0, "wit manual": 0,
    "speed ankle weights": 1, "stamina ankle weights": 3, "power ankle weights": 1, "guts ankle weights": 3,
}

ITEM_COSTS = {
    "empowering megaphone": 70,
    "vita 20": 35, "vita 40": 55, "vita 65": 75,
    "berry sweet cupcake": 55, "plain cupcake": 30,
    "glow sticks": 15, "royal kale juice": 70,
    "good-luck charm": 40, "rich hand cream": 15, "miracle cure": 40,
    "master cleat hammer": 40, "artisan cleat hammer": 25,
    "stamina scroll": 30, "speed scroll": 30, "power scroll": 30, "guts scroll": 30, "wit scroll": 30,
    "stamina manual": 15, "speed manual": 15, "power manual": 15, "guts manual": 15, "wit manual": 15,
    "speed ankle weights": 50, "stamina ankle weights": 50, "power ankle weights": 50, "guts ankle weights": 50,
}

ITEM_CAPS = {
    "empowering megaphone": 4,
    "berry sweet cupcake": 1, "plain cupcake": 3,
    "glow sticks": 3, "royal kale juice": 2, "rich hand cream": 1, "miracle cure": 1,
    "speed ankle weights": 2, "stamina ankle weights": 1, "power ankle weights": 2, "guts ankle weights": 1,
}

ITEM_NAMES = [
    "empowering megaphone",
    "vita 20", "vita 40", "vita 65",
    "berry sweet cupcake", "plain cupcake",
    "glow sticks", "royal kale juice",
    "good-luck charm", "rich hand cream", "miracle cure",
    "master cleat hammer", "artisan cleat hammer",
    "stamina scroll", "speed scroll", "power scroll", "guts scroll", "wit scroll",
    "stamina manual", "speed manual", "power manual", "guts manual", "wit manual",
    "speed ankle weights", "stamina ankle weights", "power ankle weights", "guts ankle weights",
]

ITEM_ASSETS = {
    name: os.path.join(ITEM_ASSET_ROOT, f"{name}.png")
    for name in ITEM_NAMES
}

ITEM_ALIASES = {
  "megaphone": ["empowering megaphone"],
  "race_hammer": ["master cleat hammer", "artisan cleat hammer"],
  "energy": ["vita 20", "vita 40", "vita 65", "berry sweet cupcake", "plain cupcake", "royal kale juice"],
  "bracelet": ["speed ankle weights", "stamina ankle weights", "power ankle weights", "guts ankle weights"],
  "scroll": ["stamina scroll", "speed scroll", "power scroll", "guts scroll", "wit scroll"],
  "manual": ["stamina manual", "speed manual", "power manual", "guts manual", "wit manual"],
}

BRACELET_BY_TRAINING = {
  "spd": "speed ankle weights",
  "sta": "stamina ankle weights",
  "pwr": "power ankle weights",
  "guts": "guts ankle weights",
}
CONDITION_ITEM_BY_NAME = {
  "Skin Outbreak": "rich hand cream",
}

buy_list:list[tuple[str, int]] = []

held_items = {
    "vita 20": 0,
    "vita 40": 0,
    "vita 65": 0,
    "empowering megaphone": 0,
    "royal kale juice": 0,
    "stamina ankle weights": 0,
    "power ankle weights": 0,
    "guts ankle weights": 0,
    "speed ankle weights": 0,
    "berry sweet cupcake": 0,
    "plain cupcake": 0,
    "reset whistle": 0,
    "grilled carrots": 0,
    "good-luck charm": 0,
    "rich hand cream": 0,
    "miracle cure": 0,
    "artisan cleat hammer": 0,
    "master cleat hammer": 0,
    "glow sticks": 0,
  }


def _log_missing_asset_once(path):
  if path in runtime_state["missing_assets_logged"]:
    return
  runtime_state["missing_assets_logged"].add(path)
  warning(f"Make A New Track asset missing: {path}")


def _asset_exists(path):
  exists = os.path.exists(path)
  if not exists:
    _log_missing_asset_once(path)
  return exists


def _click_box(box):
  if box:
    if len(box) == 1:
      box = box[0]
    x, y, w, h = box
    pyautogui.moveTo(x + w // 2, y + h // 2, duration=0.15)
    pyautogui.click()
    sleep(0.2)
    return True
  return False

def read_held_items():
  if not _open_items_menu():
    return False
  for i in range(3):
    if state.stop_event.is_set():
      return False
    use_item_icon = match_template("assets/mant/use_plus_button.png", threshold=0.9, use_cache = False)
    for x, y, w, h in use_item_icon:
      # the box width is 435, and the height is 60,
      region = (x - 405, y - 31, 225, 35)
      screenshot = enhanced_screenshot(region)
      text = extract_text(screenshot).lower()
      if text == "sweet cupcake berry":
        text = "berry sweet cupcake"
      amt_region =  (x - 305, y + 2, 20, 38)
      amt_screenshot = enhanced_screenshot(amt_region, 4)
      amt = extract_number(amt_screenshot)
      held_items[text] = amt
    drag_scroll(constants.SHOP_SCROLL_BOTTOM_MOUSE_POS, -500, duration=0.25, sleep_duration=0.5)
    sleep(0.2)
  sleep(0.2)
  _close_items_menu()
  print(f"Held items: {held_items}")
  return True

def _open_shop():
  shop_asset = BUTTON_ASSETS["shop"]
  button = match_template(shop_asset, threshold=0.9, use_cache = True)
  if not button:
    return False
  _click_box(button)
  sleep(0.3)
  return True

def _close_shop():
  button = match_template('assets/mant/back_shop.png', threshold=0.9, use_cache = True)
  if not button:
    return False
  _click_box(button)
  sleep(0.2)
  return True

def _open_items_menu():
  open_asset = BUTTON_ASSETS["training_items"]
  if not _asset_exists(open_asset):
    debug("Open items menu asset not found, cannot open items menu.")
    return False
  button = match_template(open_asset, threshold=0.9, use_cache = True)
  if not button:
    return False
  _click_box(button)
  return True


def _close_items_menu():
  close_asset = BUTTON_ASSETS["close_training_items"]
  if not _asset_exists(close_asset):
    return False
  button = match_template(close_asset, threshold=0.9, use_cache = True)
  if not button:
    return False
  _click_box(button)
  return True

def _use_item(item_name, times = 1):
  if not _open_items_menu():
    return False
  if item_name == "sweet cupcake berry":
    item_name = "berry sweet cupcake"
  for i in range(3):
    if state.stop_event.is_set():
      return False
    use_item_icon = match_template(f"assets/mant/{item_name}.png", threshold=0.9, use_cache = False)
    
    if use_item_icon:
      for x, y, w, h in use_item_icon:
        # the box width is 435, and the height is 60,
        region = (x + 90, y - 5, 340, 30)
        screenshot = enhanced_screenshot(region)
        text = extract_text(screenshot).lower()
        info(text)
        if text == item_name:
          # find the button position relative to the item
          button_region = (x, y, w, h)
          if is_btn_active(button_region):
            info(f"Using {text}")
            for _ in range(times):
              pyautogui.click(x=x + 485, y=y + 40, duration=0.15)
              sleep(0.2)
            _confirm_item_use()
            held_items[item_name] -= times
            while not _close_items_menu():
              sleep(0.1)
            return True
          else:
            while not _close_items_menu():
              sleep(0.1)
            return False
    drag_scroll(constants.SHOP_SCROLL_BOTTOM_MOUSE_POS, -500, duration=0.25, sleep_duration=0.5)
  _close_items_menu()
  return False

def _confirm_item_use():
  confirm_asset = BUTTON_ASSETS["confirm_use"]
  if not _asset_exists(confirm_asset):
    return False
  button = match_template(confirm_asset, threshold=0.9, use_cache = True)
  _click_box(button)
  sleep(0.5)
  confirm_asset2 = BUTTON_ASSETS["confirm_use2"]
  if not _asset_exists(confirm_asset2):
    return False
  button2 = match_template(confirm_asset2, threshold=0.9, use_cache = True)
  _click_box(button2)
  return True

def go_shopping():
  if not _open_shop():
    return False
  points_screenshot = enhanced_screenshot((700,340,70,30))
  total_points = extract_number(points_screenshot)
  debug(total_points)

  # First pass: check items and prices and build buy list
  shopping_list = []
  for i in range(5):
    subshopping_list = []
    if state.stop_event.is_set():
      return False
    buy_item_icon = match_template("assets/mant/check_box.png", threshold=0.98, use_cache = False)
    # We want some smarter way to do this probably by storing the screenshot itself instead of waiting for the screen to settle
    if buy_item_icon:
      for x, y, w, h in buy_item_icon:
        # The item name isn't directly on the shop screen, so we have to take a screenshot of the area around the checkbox and do OCR to determine which item it is
        region = (x - 365, y - 20, 230, 35)
        screenshot = enhanced_screenshot(region)
        text = extract_text(screenshot).lower()
        if text == "sweet cupcake berry":
          text = "berry sweet cupcake"
        info(text)
        turn_region = (x-13, y-25, 18, 20)
        turn_screenshot = enhanced_screenshot(turn_region, scale = 4)
        turns_number = extract_number(turn_screenshot)
        if turns_number == -1:
          print(extract_text(turn_screenshot))
          turn_screenshot.save('test.png')
        if text in ITEM_NAMES:
          subshopping_list.append((text, turns_number))
    debug(subshopping_list)
    shopping_list = merge_with_overlap_kmp(shopping_list, subshopping_list)
    drag_scroll(constants.SHOP_SCROLL_BOTTOM_MOUSE_POS, -400, sleep_duration=0.25, click = False)
    sleep(0.4)

  # Determine what to buy based on what we found
  shopping_list.sort(key = lambda x: (ITEM_PRIORITIES[x[0]], x[1]))
  debug(f"Found the following items in the shop: {shopping_list}")
  buy_list = []
  for item in shopping_list:
    item_name, turns_left = item
    item_cost = ITEM_COSTS[item_name]
    if item_cost <= total_points and held_items.get(item_name, 0) <  ITEM_CAPS.get(item_name, 5):
      buy_list.append(item)
      total_points -= item_cost
      if item_name in held_items:
        held_items[item_name] += 1
  debug(f"Based on priorities and points, the buy list is: {buy_list}")
  # Now go and buy items on the buy list
  if buy_list:
    for i in range(5):
      drag_scroll(constants.SHOP_SCROLL_BOTTOM_MOUSE_POS, 400, sleep_duration=0.2, click = False)
      sleep(0.2)
    for i in range(5):
      if state.stop_event.is_set():
        return False
      buy_item_icon = match_template("assets/mant/check_box.png", threshold=0.9, use_cache = False)

      if buy_item_icon:
        for x, y, w, h in buy_item_icon:
          region = (x - 365, y - 20, 230, 35)
          screenshot = enhanced_screenshot(region)
          text = extract_text(screenshot).lower()
          if text == "sweet cupcake berry":
            text = "berry sweet cupcake"
          turn_region = (x-13, y-25, 18, 20)
          turn_screenshot = enhanced_screenshot(turn_region, scale = 4)
          turns_number = extract_number(turn_screenshot)
          info(f"Checking {text} with {turns_number}")
          if turns_number == -1:
            print(extract_text(turn_screenshot))
            turn_screenshot.save('test.png')
          if (text, turns_number) in buy_list:
            pyautogui.click(x=x + 5, y=y + 5, duration=0.15)
            buy_list.remove((text, turns_number))
      if buy_list:
        drag_scroll(constants.SHOP_SCROLL_BOTTOM_MOUSE_POS, -400, sleep_duration=0.2, click = False)
        sleep(0.4)
      else:
        sleep(0.4)
        break
    _click_box(match_template("assets/mant/confirm.png", threshold=0.9, use_cache = True))
    sleep(0.1)
    while not _click_box(match_template("assets/mant/close.png", threshold=0.9, use_cache = True)):
      sleep(0.2)
  info(f"Items held: {held_items}")
  _close_shop()

  return True

def merge_with_overlap_kmp(a, b):
    # Build combined list with a separator that can't appear in data
    sep = object()
    combined = b + [sep] + a
    
    # Build prefix table (lps array)
    lps = [0] * len(combined)
    
    j = 0
    for i in range(1, len(combined)):
        while j > 0 and combined[i] != combined[j]:
            j = lps[j - 1]
        if combined[i] == combined[j]:
            j += 1
        lps[i] = j
    
    overlap = lps[-1]
    return a + b[overlap:]

def use_g1_hammer():
  if held_items.get("artisan cleat hammer", 0) > 0:
    return _use_item("artisan cleat hammer")
  if held_items.get("master cleat hammer", 0) > 1:
    return _use_item("master cleat hammer")
  return False

def use_finale_hammer():
  if held_items.get("master cleat hammer", 0) > 0:
    return _use_item("master cleat hammer")
  if held_items.get("artisan cleat hammer", 0) > 0:
    return _use_item("artisan cleat hammer")
  return False

def use_ankle_weights(training_name):
  bracelet_name = BRACELET_BY_TRAINING.get(training_name)
  if bracelet_name and held_items.get(bracelet_name, 0) > 0:
    return _use_item(bracelet_name)
  return False

def use_vitamin():
  # Restore at least 40 energy
  info("Checking vitamins!")
  if held_items.get("vita 65", 0) > 0:
    return _use_item("vita 65")
  if held_items.get("vita 40", 0) > 0:
    return _use_item("vita 40")
  if held_items.get("vita 20", 0) > 1: 
    return _use_item("vita 20", 2)
  if held_items.get("vita 20", 0) > 0: 
    return _use_item("vita 20")
  return False

def use_kale_juice():
  info("Checking kale juice!")
  if held_items.get("royal kale juice", 0) > 0 and held_items.get("plain cupcake", 0) == 0:
    _use_item("royal kale juice")
    return _use_item("plain cupcake")
  return False

def use_charm():
  info("Checking charms!")
  if held_items.get("good-luck charm", 0) > 0:
    return _use_item("good-luck charm")
  return False

def use_cupcake():
  if held_items.get("berry sweet cupcake", 0) > 0:
    return _use_item("berry sweet cupcake")
  if held_items.get("plain cupcake", 0) > 0:
    return _use_item("plain cupcake")
  return False

def use_megaphone():
  if held_items.get("empowering megaphone", 0) > 0:
    return _use_item("empowering megaphone")
  return False

def use_glow_sticks():
  if held_items.get("glow sticks", 0) > 0:
    return _use_item("glow sticks")
  return False

def get_energy_items_total():
  return held_items.get("vita 20", 0) * 20 + held_items.get("vita 40", 0) * 40 + held_items.get("vita 65", 0) * 65 + min(held_items.get("royal kale juice", 0), held_items.get("plain cupcake", 0) + held_items.get("berry sweet cupcake", 0)) * 100 
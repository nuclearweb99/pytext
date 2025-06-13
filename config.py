import curses
import json
import subprocess
import os
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".pytext_config.json")

def save_config(config, filename=CONFIG_FILE):
    with open(filename, "w") as f:
        json.dump(config, f, indent=4)

def load_config(filename=CONFIG_FILE):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    # Basic color pairs
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # You can add more pairs if needed
def open_config():
    script_path = os.path.abspath("config.py")
    # Use the working command you verified manually
    subprocess.Popen(f'cmd.exe /c start "" cmd.exe /k python "{script_path}"', shell=True)

def get_color_code(name):
    colors = {
        "black": curses.COLOR_BLACK,
        "red": curses.COLOR_RED,
        "green": curses.COLOR_GREEN,
        "yellow": curses.COLOR_YELLOW,
        "blue": curses.COLOR_BLUE,
        "magenta": curses.COLOR_MAGENTA,
        "cyan": curses.COLOR_CYAN,
        "white": curses.COLOR_WHITE,
        "default": -1,
    }
    return colors.get(name.lower(), curses.COLOR_WHITE)

def apply_colors(stdscr, fg_name, bg_name):
    fg = get_color_code(fg_name)
    bg = get_color_code(bg_name)
    curses.init_pair(10, fg, bg)
    stdscr.bkgd(' ', curses.color_pair(10))

def config_menu(stdscr, config):
    curses.curs_set(0)
    curses.start_color()
    init_colors()
    current = 0
    editing = False
    edit_buffer = ""

    while True:
        apply_colors(stdscr, config.get("foreground", "white"), config.get("background", "black"))
        stdscr.clear()
        stdscr.border()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 2, "Editor Configuration (q or ESC to save and exit)", curses.A_BOLD)

        for idx, (key, val) in enumerate(config.items()):
            highlight = curses.A_REVERSE if idx == current and not editing else 0
            stdscr.addstr(2 + idx, 4, f"{key}: ", highlight)
            if idx == current and editing:
                stdscr.addstr(f"{edit_buffer}_", curses.A_UNDERLINE)
            else:
                stdscr.addstr(str(val))

        stdscr.refresh()

        key = stdscr.getch()

        if editing:
            if key in (curses.KEY_ENTER, 10, 13):
                # Save edit
                config[list(config.keys())[current]] = edit_buffer
                editing = False
            elif key == 27:  # ESC to cancel edit
                editing = False
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                edit_buffer = edit_buffer[:-1]
            elif 32 <= key <= 126:
                edit_buffer += chr(key)
        else:
            if key == curses.KEY_UP:
                current = (current - 1) % len(config)
            elif key == curses.KEY_DOWN:
                current = (current + 1) % len(config)
            elif key in (10, 13):  # Enter to edit
                editing = True
                edit_buffer = str(config[list(config.keys())[current]])
            elif key in (27, ord('q')):
                break
    curses.curs_set(0)
    return config

def main():
    config = load_config() or {
        "tab_size": "4",
        "show_line_numbers": "yes",
        "foreground": "white",
        "background": "blue",
        "selected_debugger": "python.exe",
        "keyword":"cyan",
        "string":"yellow",
        "comment":"green",
        "builtin":"magenta"
    }
    updated_config = curses.wrapper(config_menu, config)
    save_config(updated_config)
    print("Config saved:", updated_config)

if __name__ == "__main__":
    main()
    
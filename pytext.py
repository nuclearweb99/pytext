import curses
import copy
import actions as command
import os
import config as cfg
import json
import subprocess
import sys
import pdb
import debug as dbg
import random
import keyword
import tokenize
import io
VERSION = 0
def clamp_cursor(text, row, col):
    row = max(0, min(row, len(text) - 1))
    col = max(0, min(col, len(text[row])))
    return row, col

def main(stdscr):
    curses.curs_set(1)
    stdscr.keypad(True)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    startup_path = os.path.join(script_dir, "startup.txt")
    text = command.load(startup_path)
    os.system(f"title PyText IDE Version {VERSION}")
    # Initialize other state variables
    row = 0
    col = 0
    undo_stack = []
    redo_stack = []
    filename = "startup.txt"  # default filename for save
    scroll=0
    search_query = ""
    search_results = []
    search_index = 0


    cfg_data = cfg.load_config()
    if cfg_data is None:
        cfg_data = cfg.load_config() or {
        "tab_size": "4",
        "show_line_numbers": "yes",
        "foreground": "white",
        "background": "blue",
        "selected_debugger": "python.exe",
        "keyword":"cyan",
        "string":"yellow",
        "comment":"green",
        "builtin":"magenta",
        "show_whitespace":"yes"
    }
    curses.start_color()
    curses.use_default_colors()
    fg = cfg.get_color_code(cfg_data["foreground"])
    bg = cfg.get_color_code(cfg_data["background"])
    project_path = cfg_data.get("project_path") or os.getcwd()
    curses.init_pair(1, fg, bg)
    stdscr.bkgd(' ', curses.color_pair(1))
    def save_undo():
        undo_stack.append((copy.deepcopy(text), row, col))
        if len(undo_stack) > 100:
            undo_stack.pop(0)
    def input_box(stdscr, prompt="", maxlen=120):
        h, w = stdscr.getmaxyx()
        input_text = ""
        while True:
            stdscr.addstr(h - 2, 0, prompt + input_text.ljust(w - len(prompt) - 1))
            stdscr.move(h - 2, len(prompt) + len(input_text))
            stdscr.refresh()
            key = stdscr.getch()
            if key in (10, 13):  # Enter
                return input_text
            elif key in (27,):  # ESC cancel
                return None
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                input_text = input_text[:-1]
            elif 32 <= key <= 126 and len(input_text) < maxlen:
                input_text += chr(key)
    def get_color(name):
        return cfg.get_color_code(cfg_data.get(name, "white"))

    curses.init_pair(1, get_color("foreground"), get_color("background"))  # Default text
    curses.init_pair(2, get_color("keyword"), get_color("background"))     # Keywords
    curses.init_pair(3, get_color("string"), get_color("background"))      # Strings
    curses.init_pair(4, get_color("comment"), get_color("background"))     # Comments
    curses.init_pair(5, get_color("builtin"), get_color("background"))     # Built-ins

    def open_config_in_window(stdscr, config, filename):
        h, w = stdscr.getmaxyx()
        win_h, win_w = h - 4, w - 10
        win_y, win_x = 2, 5
        cfg_data = None
        # Create a new window for config menu
        config_win = stdscr.subwin(win_h, win_w, win_y, win_x)
        config_win.box()
        config_win.refresh()

        # Pass this config window to your config menu
        updated_config = cfg.config_menu(stdscr, cfg_data)


        # Clear the config window after done
        config_win.clear()
        stdscr.touchwin()
        stdscr.refresh()

        return updated_config
    def draw_line_with_syntax(stdscr, y, line, w, cfg_data, search_query="", fn=""):
        show_ws = cfg_data.get("show_whitespace", "no") == "yes"
        COLOR_DEFAULT = curses.color_pair(1)
        COLOR_KEYWORD = curses.color_pair(2)
        COLOR_STRING  = curses.color_pair(3)
        COLOR_COMMENT = curses.color_pair(4)
        COLOR_BUILTIN = curses.color_pair(5)

        line_str = "".join(line)
        PY_EXTENSIONS = (".py", ".pyw")

        # If file is NOT a Python file, just draw default color
        if not fn.lower().endswith(PY_EXTENSIONS):
            # Show visible whitespace if enabled
            raw = "".join(" " if c == " " and show_ws else c for c in line_str[:w])
            try:
                if search_query:
                    # Highlight search query matches
                    start = 0
                    while True:
                        idx = raw.find(search_query, start)
                        if idx == -1:
                            stdscr.addstr(y, 0, raw[start:], COLOR_DEFAULT)
                            break
                        if idx > start:
                            stdscr.addstr(y, start, raw[start:idx], COLOR_DEFAULT)
                        stdscr.addstr(y, idx, raw[idx:idx+len(search_query)], COLOR_DEFAULT | curses.A_REVERSE)
                        start = idx + len(search_query)
                else:
                    stdscr.addstr(y, 0, raw, COLOR_DEFAULT)
            except curses.error:
                pass
            return

        # --- For Python files, do syntax coloring ---
        tokens = []
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(line_str).readline))
        except tokenize.TokenError:
            pass

        color_map = [COLOR_DEFAULT] * len(line_str)

        # Mark colors according to tokens
        for tok_type, tok_str, (srow, scol), (erow, ecol), _ in tokens:
            attr = COLOR_DEFAULT
            if tok_type == tokenize.COMMENT:
                attr = COLOR_COMMENT
            elif tok_type == tokenize.STRING:
                attr = COLOR_STRING
            elif tok_type == tokenize.NAME:
                if tok_str in keyword.kwlist:
                    attr = COLOR_KEYWORD
                elif tok_str in dir(__builtins__):
                    attr = COLOR_BUILTIN
            for i in range(scol, min(ecol, len(color_map))):
                color_map[i] = attr

        for i, c in enumerate(line_str[:w]):
            ch = " " if c == " " and show_ws else c
            attr = color_map[i]
            # Highlight search query in Python code
            if search_query and line_str[i:i+len(search_query)] == search_query:
                attr |= curses.A_REVERSE
            try:
                stdscr.addch(y, i, ch, attr)
            except curses.error:
                pass

        def init_color_pairs(cfg_data):
            # Map names to curses colors
            def get_color(name):
                return cfg.get_color_code(name)

            curses.init_pair(1, get_color(cfg_data["foreground"]), get_color(cfg_data["background"]))
            curses.init_pair(2, get_color(cfg_data["keyword"]), get_color(cfg_data["background"]))
            curses.init_pair(3, get_color(cfg_data["string"]), get_color(cfg_data["background"]))
            curses.init_pair(4, get_color(cfg_data["comment"]), get_color(cfg_data["background"]))
            curses.init_pair(5, get_color(cfg_data["builtin"]), get_color(cfg_data["background"]))
        init_color_pairs(cfg_data)
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        visible_lines = h - 1  # Reserve 1 line for status

        # Adjust scroll to keep cursor visible
        if row < scroll:
                scroll = row
        elif row >= scroll + visible_lines:
                scroll = row - visible_lines + 1

            # Draw text
        for i in range(scroll, min(scroll + visible_lines, len(text))):
                try:
                    for i in range(scroll, min(scroll + visible_lines, len(text))):
                        draw_line_with_syntax(stdscr, i - scroll, text[i], w, cfg_data, search_query, filename)
                except curses.error:
                    pass

            # Status bar
        status = f"Ctrl+T: Run Command | {row}, {col} | Editing: {filename}"
        stdscr.addstr(h - 1, 0, status[:w - 1], curses.A_REVERSE)
        # Clamp and move cursor
        row, col = clamp_cursor(text, row, col)
        try:
            stdscr.move(row - scroll, col)
        except curses.error:
            pass
            
        stdscr.refresh()
        key = stdscr.getch()

        if key == 17:  # Ctrl+Q
            break

        elif key == 26:  # Ctrl+Z
            if undo_stack:
                redo_stack.append((copy.deepcopy(text), row, col))
                text, row, col = undo_stack.pop()
                row, col = clamp_cursor(text, row, col)

        elif key == 25:  # Ctrl+Y
            if redo_stack:
                undo_stack.append((copy.deepcopy(text), row, col))
                text, row, col = redo_stack.pop()
                row, col = clamp_cursor(text, row, col)
        if key == 20:
            cmd = input_box(stdscr)
            if cmd:
                parts = cmd.split(maxsplit=1)
                if len(parts) == 1:
                    action = parts[0]
                    if action == ":save":
                        if filename.lower() == "untitled":
                            new_name = input_box(stdscr, "Save as: ")
                            if new_name:
                                filename = new_name
                                fullpath = os.path.join(project_path, filename)
                            else:
                                return
                        try:
                            command.save(filename, text)
                        except Exception as e:
                            stdscr.addstr(h - 2, 0, f"Save failed: {str(e)}", curses.A_REVERSE)
                            stdscr.refresh()
                            stdscr.getch()
                    elif cmd.startswith(":setpath"):
                        new_path = input_box(stdscr, "New project path: ")
                        if new_path and os.path.isdir(new_path):
                            project_path = new_path
                            cfg_data["project_path"] = new_path
                            cfg.save_config(cfg_data)
                        else:
                            stdscr.addstr(h - 1, 0, "Invalid path.".ljust(w - 1), curses.A_REVERSE)
                            stdscr.refresh()
                            curses.napms(1000)
                    elif action == ":config":
                        cfg_data = cfg.config_menu(stdscr, cfg_data)
                        cfg.save_config(cfg_data)
                    elif action == ":load":
                        filename_input = input_box(stdscr, "Load file: ")
                        if filename_input:
                            fullpath = os.path.join(project_path, filename_input)
                            if os.path.exists(fullpath):
                                text = command.load(fullpath)
                                filename = filename_input
                            else:
                                status_msg = f"File not found: {fullpath}"
                    elif action == ":dbgcon":
                        cfg_data = dbg.debugger_manager(stdscr, cfg_data)
                        cfg.save_config(cfg_data)
                    elif action == ":exit":
                        curses.endwin()
                        return
                    elif action == ":new":
                        text = [[]]
                        row = 0
                        col = 0
                        undo_stack = []
                        redo_stack = []
                        filename = "untitled"
                        scroll = 0
                    elif action == ":debug":
                        dbg.launch_debugger(cfg_data, filename, stdscr, text)    
                    elif cmd.strip() == ":find":
                        query = input_box(stdscr, "Find: ")
                        if query:
                            search_query = query
                            search_results = []
                            search_index = 0

                            for i, line in enumerate(text):
                                joined = "".join(line)
                                col = joined.find(query)
                                while col != -1:
                                    search_results.append((i, col))
                                    col = joined.find(query, col + 1)

                            if search_results:
                                row, col = search_results[0]
                            else:
                                status_msg = f"'{query}' not found"
                    elif action == ":goto":
                        line_input = input_box(stdscr, "Go to line: ")
                        if line_input and line_input.isdigit():
                            line_num = int(line_input) - 1
                            if 0 <= line_num < len(text):
                                row = line_num
                                col = min(col, len(text[row]))
                    elif action == ":findc":
                        search_query = ""
                        search_results = []
                        search_index = 0
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if col > 0:
                save_undo()
                text[row].pop(col - 1)
                col -= 1
            elif row > 0:
                save_undo()
                col = len(text[row - 1])
                text[row - 1].extend(text[row])
                text.pop(row)
                row -= 1

        elif key == 10:  # Enter
            save_undo()
            new_line = text[row][col:]
            text[row] = text[row][:col]
            text.insert(row + 1, new_line)
            row += 1
            col = 0

        elif key == curses.KEY_LEFT:
            if col > 0:
                col -= 1
            elif row > 0:
                row -= 1
                col = len(text[row])
        elif key == 9:
            save_undo()
            for _ in range(4):  # Insert 4 spaces
                text[row].insert(col, ' ')
                col += 1

        elif key == curses.KEY_RIGHT:
            if col < len(text[row]):
                col += 1
            elif row + 1 < len(text):
                row += 1
                col = 0

        elif key == curses.KEY_UP:
            if row > 0:
                row -= 1
                col = min(col, len(text[row]))

        elif key == curses.KEY_DOWN:
            if row + 1 < len(text):
                row += 1
                col = min(col, len(text[row]))

        elif 32 <= key <= 126:
            save_undo()
            text[row].insert(col, chr(key))
            col += 1

        # Clear redo stack on new edits
        if key not in (26, 25):  # not undo/redo
            redo_stack.clear()

        row, col = clamp_cursor(text, row, col)
def run_editor():
    try:
        curses.wrapper(main)
    except Exception as e:
        
        try:
            curses.endwin()
        except:
            pass
        print("PyText has crashed.")
        funny_messages=[
            "It's your fault!",
            "OOOOPS!",
            "You should have used a real editor.",
            "Sorry, not sorry.",
            "Fix it yourself!",
            "You broke it, you fix it.",
            "You suck!",
            "You're a terrible programmer.",
            "Tell the duck!"
        ]
        print(random.choice(funny_messages))
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")  # Prevents cmd.exe from closing

run_editor()
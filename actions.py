import os
import config as cfg
cfg_data = cfg.load_config()
if cfg_data is None:
    cfg_data = {
    "tab_size": "4",
    "show_line_numbers": "yes",
    "foreground": "white",
    "background": "blue",
    "selected_debugger": "python.exe",
    "debug_internal": "True"
}
def save(filename, text):
    if not filename or not isinstance(filename, str):
        raise ValueError("Invalid filename.")

    # If no path is given, save in script directory (safe default)
    if not os.path.isabs(filename):
        script_dir = cfg_data["project_path"]
        filename = os.path.join(script_dir, filename)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("")
            for line in text:
                f.write("".join(line) + "\n")
    except Exception as e:
        raise RuntimeError(f"Could not save file '{filename}': {e}")

def load(filename):
    if not os.path.exists(filename):
        return [[]]  # Empty buffer if file doesn't exist

    try:
        with open(filename, "r", encoding='utf-8') as f:
            lines = f.readlines()
        return [list(line.rstrip("\n")) for line in lines]
    except Exception as e:
        raise RuntimeError(f"Could not load file '{filename}': {e}")
def find_text(text, query, start_row=0, start_col=0):
            for i in range(start_row, len(text)):
                line = "".join(text[i])
                col = line.find(query, start_col if i == start_row else 0)
                if col != -1:
                    return i, col
            return None, None

def replace_text(text, old, new, replace_all=False):
    replaced = 0
    for i in range(len(text)):
        line = "".join(text[i])
        if old in line:
            if replace_all:
                line = line.replace(old, new)
            else:
                line = line.replace(old, new, 1)
            text[i] = list(line)
            replaced += 1
            if not replace_all:
                break
    return replaced
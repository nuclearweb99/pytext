import curses
import sys
import subprocess
import os
import config as cfg
def launch_debugger(config, filename, stdscr, text):
    selected_dbg = config.get("selected_debugger", "python.exe")

    # Save the file first if needed
    if filename:
        if not os.path.isabs(filename):
            # Use project path or user's home dir if cwd is unsafe
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
            cwd = cfg_data["project_path"]
            filename = os.path.join(cwd, filename)

        try:
            with open(filename, 'w') as f:
                f.write("") # SHITTY HACK! NO WORK! TAKE YOUR EYES OF THIS CODE!
                for line in text:
                    f.write("".join(line) + '\n')
        except Exception as e:
            print(e)
            stdscr.addstr(0, 0, f"Failed to save: {e}", curses.A_REVERSE)
            stdscr.refresh()
            stdscr.getch()
            return

    # Exit curses before spawning a new process
    curses.endwin()

    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", selected_dbg, filename],
                shell=True
            )
        else:
            subprocess.Popen([selected_dbg, filename])
    except Exception as e:
        print("Debugger launch failed:", e)
    finally:
        # Pause briefly or wait for user input if needed
        input("Press Enter to return to the IDE...")
def debug_in_ide(stdscr, filename, text):
    # Temporarily exit curses UI
    curses.endwin()

    # Save current file contents to disk before debugging
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for line in text:
                f.write("".join(line) + "\n")
    except Exception as e:
        print(f"Error saving before debugging: {e}")
        input("Press Enter to return...")
        curses.initscr()
        return

    # Launch pdb
    try:
        import pdb
        print(f"\nRunning debugger on {filename}. Use Escape to stop.\n")
        pdb.run(f'exec(open("{filename}").read())', globals(), locals())
    except Exception as e:
        print("Debugger crashed:")
        import traceback
        traceback.print_exc()
    input("\nPress Enter to return to the editor...")

    # Reinitialize curses
    stdscr.clear()
    curses.doupdate()
    curses.initscr()
    curses.curs_set(1)

def debugger_manager(stdscr, config):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "Debugger Manager - Press q to quit", curses.A_BOLD)

    # Dummy debug executables list in config or default
    debuggers = config.get("debuggers", ["python.exe", "gdb", "lldb"])
    selected = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Debugger Manager - Select debugger (q to quit)", curses.A_BOLD)

        for i, dbg in enumerate(debuggers):
            attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
            stdscr.addstr(2 + i, 2, dbg, attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(debuggers)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(debuggers)
        elif key in (10, 13):  # Enter key
            # Save selected debugger in config and exit
            config["selected_debugger"] = debuggers[selected]
            break
        elif key in (ord('q'), 27):  # q or ESC to quit without changes
            break

    curses.curs_set(1)
    return config

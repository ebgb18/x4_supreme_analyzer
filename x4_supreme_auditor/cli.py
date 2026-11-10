# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
import argparse
import glob
import json
import os
import sys
import webbrowser

from .constants import DEFAULT_GAME_DIR
from .utils import num
from .gamedata import GameData, Namer
from .parser import SaveParser
from .dossier import build_dossier
from .terminal import generate_command_terminal_html

def find_game_dir(user_arg):
    candidates = [
        user_arg, DEFAULT_GAME_DIR, os.environ.get("X4_GAME_DIR"),
        r"C:\Program Files (x86)\Steam\steamapps\common\X4 Foundations",
        r"D:\SteamLibrary\steamapps\common\X4 Foundations",
        r"F:\genisis\X4.Foundations-SteamRIP.com\X4 Foundations Envoy Pack"
    ]
    for c in candidates:
        if c and os.path.isdir(c): return c
    return None

def find_default_save():
    for f in sorted(os.listdir("."), reverse=True):
        if (f.endswith(".xml.gz") or f.endswith(".xml")) and not f.startswith("x4_"):
            return f
    docs = os.path.expanduser(r"~\Documents\Egosoft\X4")
    if os.path.isdir(docs):
        saves = glob.glob(os.path.join(docs, "*", "save", "*.xml.gz"))
        if saves:
            return max(saves, key=os.path.getmtime)
    return None

def main():
    parser = argparse.ArgumentParser(description="X4: Foundations Supreme Command & Empire Intelligence Terminal (V1.7.7 Enterprise - Supreme Intelligence Edition)")
    parser.add_argument("save", nargs="?", help="Path to save file (.xml or .xml.gz)")
    parser.add_argument("--game-dir", default=DEFAULT_GAME_DIR, help="Path to unpacked X4 game data directory")
    parser.add_argument("--out", default="x4_master_empire_dossier.md", help="Output Markdown report path")
    parser.add_argument("--html", default="x4_command_terminal.html", help="Interactive tactical terminal HTML path")
    parser.add_argument("--names", default="x4_sector_names.json", help="Optional sector name override JSON")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser terminal")
    args = parser.parse_args()

    save_path = args.save or find_default_save()
    if not save_path or not os.path.isfile(save_path):
        sys.exit("[-] Error: No valid savegame found. Provide a .xml or .xml.gz save file.")

    gdir = find_game_dir(args.game_dir)
    print(f"[*] Initializing Game Data Engine from: {gdir}")
    gd = GameData(gdir) if gdir else None

    overrides = {}
    if os.path.isfile(args.names):
        try:
            with open(args.names, encoding="utf-8") as fh:
                overrides = {k.lower(): v for k, v in json.load(fh).items() if not k.startswith("_")}
        except Exception as e: print(f"[-] Warning reading {args.names}: {e}")

    namer = Namer(gd if (gd and gd.ok) else None, overrides)

    print(f"[*] Parsing savegame: {save_path}")
    P = SaveParser()
    P.parse(save_path)
    if P.truncated:
        sys.exit(f"[-] Error: Savegame XML is malformed or truncated ({P.truncated}). No reports generated.")
    P.finalize()

    report, net_worth, liquid, fleet_val, st_val, stock_val = build_dossier(P, namer, gdir, bool(gd and gd.ok))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"[+] Markdown dossier compiled -> {args.out}")

    generate_command_terminal_html(P, namer, args.html, net_worth, liquid, fleet_val, st_val, stock_val)

    if not args.no_browser:
        full_html_path = os.path.abspath(args.html)
        print(f"[*] Launching Supreme Command Terminal -> {full_html_path}")
        webbrowser.open(f"file://{full_html_path}")

    print(f"[+] Terminal deployment complete. Empire Net Worth: {num(net_worth)} Credits.")

if __name__ == "__main__":
    main()
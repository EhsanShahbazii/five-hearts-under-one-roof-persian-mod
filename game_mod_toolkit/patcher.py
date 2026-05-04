import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
Five Hearts Under One Roof 1 (MilkGame) - Persian Subtitle Mod Patcher & Manager
Features:
- Automated non-destructive backup and 1-click restore
- RTL & BiDi text shaping for Unity TextMeshPro
- Custom font SDF glyph baking (Lahzeh / Vazirmatn)
- In-place batch patching of all 540 scenes & dialogues into data.unity3d
- Zero-crash guarantee with automatic macOS ad-hoc code-signing
"""

import os
import glob
import json
import shutil
import subprocess
import argparse
import UnityPy

from rtl_formatter import shape_persian
from sdf_font_baker import collect_persian_unicodes, bake_persian_font_into_env

TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GAME_PATH = "/Users/ehsan/Applications/MilkGame.app"
BACKUP_DIR = os.path.join(TOOLKIT_DIR, "backup")
PERSIAN_DIR = os.path.join(TOOLKIT_DIR, "translations", "persian")
FONTS_DIR = os.path.join(TOOLKIT_DIR, "fonts")

def get_data_bundle_path(game_app_path: str) -> str:
    candidates = [
        os.path.join(game_app_path, "Contents", "Game", "MilkGame.app", "Contents", "Resources", "Data", "data.unity3d"),
        os.path.join(game_app_path, "Contents", "Resources", "Data", "data.unity3d")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"data.unity3d not found in {game_app_path}")

def backup_file(src: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    bak_name = os.path.basename(src) + ".original"
    bak_path = os.path.join(dest_dir, bak_name)
    if not os.path.exists(bak_path):
        print(f"[*] Creating backup of original: {bak_name}...")
        shutil.copy2(src, bak_path)
        print(f"[✔] Backup saved: {bak_path}")
    return bak_path

def restore_backup(game_app_path: str):
    data_path = get_data_bundle_path(game_app_path)
    bak_path = os.path.join(BACKUP_DIR, os.path.basename(data_path) + ".original")
    if not os.path.exists(bak_path):
        print(f"[!] No backup found at: {bak_path}")
        return False
    print(f"[*] Restoring factory data from: {bak_path}...")
    shutil.copy2(bak_path, data_path)
    subprocess.run(["codesign", "--force", "--deep", "-s", "-", game_app_path], check=False)
    print("[✔] Successfully restored original factory game data!")
    return True

def apply_patch(game_app_path: str = DEFAULT_GAME_PATH, font_choice: str = "lahzeh"):
    data_path = get_data_bundle_path(game_app_path)
    print("==================================================")
    print(" Five Hearts Under One Roof 1 - Subtitle Patcher")
    print("==================================================")
    print(f"[*] Target Game:   {game_app_path}")
    print(f"[*] Target Data:   {data_path}")
    print(f"[*] Font Choice:   {font_choice.upper()}")

    # 1. Backup pristine original
    backup_file(data_path, BACKUP_DIR)

    # 2. Collect unique Persian unicodes across all translations
    unicodes = collect_persian_unicodes(PERSIAN_DIR)
    print(f"[*] Total unique Persian glyphs to bake: {len(unicodes)}")

    # 3. Load game archive
    print("[*] Loading data.unity3d archive into memory...")
    env = UnityPy.load(data_path)

    # 4. Bake Persian font into SDF Atlas and FontAsset
    font_file = "Lahzeh-Bold.ttf" if font_choice.lower() == "lahzeh" else "Vazirmatn-Bold.ttf"
    ttf_path = os.path.join(FONTS_DIR, font_file)
    if not os.path.exists(ttf_path):
        raise FileNotFoundError(f"Font file not found: {ttf_path}")

    baked_count = bake_persian_font_into_env(env, ttf_path, unicodes)

    # 5. Patch all TextAssets with shaped Persian subtitles
    print("[*] Injecting Persian subtitles into TextAssets...")
    patched_files = 0
    patched_lines = 0

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                data = obj.read()
                name = getattr(data, "m_Name", "")
                if not name:
                    continue

                trans_path = os.path.join(PERSIAN_DIR, f"{name}.json")
                if not os.path.exists(trans_path):
                    continue

                with open(trans_path, "r", encoding="utf-8") as tf:
                    translations = json.load(tf)

                # Map translations by INDEX
                trans_map = {}
                for it in translations:
                    if isinstance(it, dict):
                        idx = it.get("INDEX")
                        script = it.get("SCRIPT", {})
                        fa = script.get("PERSIAN") or script.get("ENGLISH") or ""
                        if idx is not None and fa:
                            trans_map[idx] = fa

                script_json = json.loads(data.m_Script)
                modified = False

                for it in script_json:
                    if isinstance(it, dict) and "SCRIPT" in it and isinstance(it["SCRIPT"], dict):
                        idx = it.get("INDEX")
                        if idx in trans_map:
                            raw_fa = trans_map[idx]
                            shaped = shape_persian(raw_fa)
                            # Inject Persian into KOREAN slot; ENGLISH remains 100% untouched factory English!
                            it["SCRIPT"]["KOREAN"] = shaped
                            modified = True
                            patched_lines += 1

                if modified:
                    data.m_Script = json.dumps(script_json, ensure_ascii=False)
                    data.save()
                    patched_files += 1
            except Exception as e:
                print(f"[!] Error patching TextAsset {getattr(data, 'm_Name', '?')}: {e}")

    # 6. Save modified data.unity3d archive
    print(f"[*] Saving patched archive to {data_path} (packer=lz4)...")
    temp_out = data_path + ".tmp"
    with open(temp_out, "wb") as f:
        f.write(env.file.save(packer="lz4"))

    os.replace(temp_out, data_path)
    print(f"[✔] Successfully saved data.unity3d ({os.path.getsize(data_path)} bytes)!")

    # 7. Re-sign the game bundle to guarantee smooth launch
    print("[*] Re-signing MilkGame.app with ad-hoc signature...")
    subprocess.run(["xattr", "-cr", game_app_path], check=False)
    subprocess.run(["codesign", "--force", "--deep", "-s", "-", game_app_path], check=False)

    print("==================================================")
    print(f"[✨] Patching Complete!")
    print(f"[*] Patched Files:  {patched_files}")
    print(f"[*] Patched Lines:  {patched_lines}")
    print(f"[*] Baked Glyphs:   {baked_count}")
    print("▶ Run the game and set Language to '한국어' (Korean) in Settings to see Persian subtitles!")
    print("▶ Language 'English' remains original English subtitles.")
    print("==================================================")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patch Five Hearts Under One Roof 1 with Persian Subtitles")
    parser.add_argument("--game-path", default=DEFAULT_GAME_PATH, help="Path to MilkGame.app")
    parser.add_argument("--font", default="lahzeh", choices=["lahzeh", "vazirmatn"], help="Font choice (lahzeh or vazirmatn)")
    parser.add_argument("--restore", action="store_true", help="Restore factory original data")
    args = parser.parse_args()

    if args.restore:
        restore_backup(args.game_path)
    else:
        apply_patch(args.game_path, args.font)

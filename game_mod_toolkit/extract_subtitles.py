"""
Subtitle & Script Extractor for Five Hearts Under One Roof 1 (MilkGame)
Extracts all dialogue, choices, episodes, endings, objects, chats, and UI string tables
from data.unity3d into structured, readable JSON files.
"""

import os
import json
import argparse
import UnityPy

DEFAULT_GAME_PATH = "/Users/ehsan/Applications/MilkGame.app"

def get_data_bundle_path(game_app_path: str) -> str:
    # Check both inner and outer structure
    candidates = [
        os.path.join(game_app_path, "Contents", "Game", "MilkGame.app", "Contents", "Resources", "Data", "data.unity3d"),
        os.path.join(game_app_path, "Contents", "Resources", "Data", "data.unity3d")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"data.unity3d not found in {game_app_path}")

def extract_all(game_app_path: str, output_dir: str):
    data_path = get_data_bundle_path(game_app_path)
    print(f"[*] Loading data archive: {data_path} ({os.path.getsize(data_path)} bytes)...")
    env = UnityPy.load(data_path)

    os.makedirs(output_dir, exist_ok=True)
    extracted_count = 0
    total_lines = 0

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                data = obj.read()
                name = getattr(data, "m_Name", "")
                content = getattr(data, "m_Script", "")
                if not content or not name:
                    continue

                try:
                    parsed = json.loads(content)
                except Exception:
                    continue

                # Check if this TextAsset is a dialogue / script table or string table
                is_script = False
                lines = 0
                if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                    if "SCRIPT" in parsed[0]:
                        is_script = True
                        lines = len(parsed)
                    elif any(k in name.upper() for k in ["CHAPTER", "ACHIEVEMENT", "PROFILE", "RANKING"]):
                        is_script = True
                        lines = len(parsed)

                if is_script:
                    out_path = os.path.join(output_dir, f"{name}.json")
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False, indent=2)
                    extracted_count += 1
                    total_lines += lines
                    if extracted_count <= 5 or extracted_count % 50 == 0:
                        print(f" [+] Extracted: {name}.json ({lines} lines)")
            except Exception as e:
                print(f"[!] Error processing TextAsset: {e}")

    print("==================================================")
    print(f"[✔] Total extracted script files: {extracted_count}")
    print(f"[✔] Total dialogue/script lines:  {total_lines}")
    print(f"[✔] Saved to: {output_dir}")
    print("==================================================")
    return extracted_count, total_lines

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract game subtitles from data.unity3d")
    parser.add_argument("--game-path", default=DEFAULT_GAME_PATH, help="Path to MilkGame.app")
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "translations", "raw"), help="Output directory")
    args = parser.parse_args()

    extract_all(args.game_path, args.out_dir)

import os
import zipfile
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ZIP_1 = os.path.join(ROOT_DIR, "AetherPravah_Project.zip")
OUTPUT_ZIP_2 = os.path.join("C:\\Users\\bhumika\\OneDrive\\Desktop", "AetherPravah_Project.zip")

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".next",
    ".turbo",
    ".cache",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".zip",
    ".log",
}

def create_zip():
    print(f"Creating clean zip from {ROOT_DIR}...")
    temp_zip = os.path.join(ROOT_DIR, "_temp_pack.zip")
    if os.path.exists(temp_zip):
        os.remove(temp_zip)

    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".git")]
            
            rel_root = os.path.relpath(root, ROOT_DIR)
            if rel_root == ".":
                rel_root = ""

            for file in files:
                if any(file.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue
                if file.startswith("_temp_"):
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.join(rel_root, file) if rel_root else file
                zf.write(full_path, rel_path)

    # Move temp zip to destinations
    shutil.copy2(temp_zip, OUTPUT_ZIP_1)
    try:
        shutil.copy2(temp_zip, OUTPUT_ZIP_2)
        print(f"Copied to Desktop: {OUTPUT_ZIP_2}")
    except Exception as e:
        print(f"Warning copying to desktop: {e}")
    os.remove(temp_zip)
    print(f"Clean archive created successfully: {os.path.getsize(OUTPUT_ZIP_1)} bytes")

if __name__ == "__main__":
    create_zip()

"""
TextQuicker 打包脚本
自动安装依赖，然后用 PyInstaller 打包成单文件 EXE
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

def run(cmd, cwd=None, check=True):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_DIR)
    if check and result.returncode != 0:
        print(f"命令失败，退出码: {result.returncode}")
        sys.exit(result.returncode)
    return result

def main():
    print("=" * 60)
    print("  TextQuicker 打包工具")
    print("=" * 60)

    # 1. 安装依赖
    print("\n[1/3] 安装依赖库...")
    deps = ["keyboard", "pyperclip", "pywin32", "pystray", "Pillow", "pyinstaller"]
    for dep in deps:
        run(f'"{sys.executable}" -m pip install {dep} -q')

    # 2. 打包
    print("\n[2/3] 开始打包...")
    src = os.path.join(SCRIPT_DIR, "text_quicker.py")
    out_dir = os.path.join(PROJECT_DIR, "dist_textquicker")

    cmd = (
        f'"{sys.executable}" -m PyInstaller '
        f'--onefile '
        f'--windowed '
        f'--name "TextQuicker" '
        f'--distpath "{out_dir}" '
        f'--clean '
        f'"{src}"'
    )
    run(cmd)

    # 3. 完成
    exe = os.path.join(out_dir, "TextQuicker.exe")
    if os.path.exists(exe):
        size = os.path.getsize(exe) / 1024 / 1024
        print(f"\n[3/3] 打包成功！")
        print(f"  路径: {exe}")
        print(f"  大小: {size:.1f} MB")
    else:
        print("\n未找到输出文件，请检查上方日志。")

if __name__ == "__main__":
    main()

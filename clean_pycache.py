import os
import shutil


def delete_pycache_dirs(root_path="."):
    deleted_count = 0
    for dirpath, dirnames, filenames in os.walk(root_path):
        if "__pycache__" in dirnames:
            pycache_path = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print(f"✅ 删除: {pycache_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败: {pycache_path}，错误: {e}")
    if deleted_count == 0:
        print("🤔 没有找到任何 __pycache__ 文件夹。")
    else:
        print(f"\n🎉 总共删除了 {deleted_count} 个 __pycache__ 文件夹。")


if __name__ == "__main__":
    delete_pycache_dirs()

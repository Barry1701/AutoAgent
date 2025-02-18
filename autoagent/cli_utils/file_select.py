import tkinter as tk
from tkinter import filedialog
import shutil
import os
from rich.console import Console

def select_and_copy_files(dest_dir, console: Console, docker_files_dir: str):
    # 创建 tkinter 根窗口但隐藏它
    root = tk.Tk()
    root.withdraw()

    # 打开文件选择对话框
    files = filedialog.askopenfilenames(
        title='Select files to copy',
        filetypes=[
            # ('Text files', '*.txt'),
            ('All files', '*.*'),
            ('PDF files', '*.pdf'),
            ('Docx files', '*.docx'),
            ('Txt files', '*.txt'),
            ('Zip files', '*.zip'),
            ('Text files', '*.txt'),
        ]
    )
    
    if not files:
        print("No files selected")
        return

    # 选择目标文件夹
    # dest_dir = filedialog.askdirectory(
    #     title='Select destination folder'
    # )
    
    if not dest_dir:
        print("No destination folder selected")
        return

    # 复制文件
    upload_infos = []
    for file_path in files:
        file_name = os.path.basename(file_path)
        dest_path = os.path.join(dest_dir, file_name)
        docker_dest_path = os.path.join(docker_files_dir, file_name)
        try:
            shutil.copy2(file_path, dest_path)
            msg = f"Uploaded: {file_name} to {docker_dest_path}"
            upload_infos.append(msg)
            console.print(f"[bold green]{msg}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error uploading {file_name}: {e}[/bold red]")

    console.print(f"[bold green]Successfully uploaded {len(files)} files[/bold green]")
    return upload_infos
if __name__ == "__main__":
    dest_dir = "/Users/tangjiabin/Documents/reasoning/metachain/workspace_meta_showcase/showcase_nl2agent_showcase/workplace"
    select_and_copy_files(dest_dir)
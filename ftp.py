from ftplib import FTP_TLS as FTP
from pathlib import Path
import os
from time import time
import toml

start = time()

path = Path(__file__).parent.resolve()

cfg_path = path / "config.toml"
with open(cfg_path, "r") as file:
    data = file.read()
    config = toml.loads(data)

print("Logging in to the server...")

server_cfg = config["server"]
ftp = FTP(
    server_cfg["host"],
    server_cfg["user"],
    server_cfg["password"]
)
ftp.prot_p()

print("  Successful login")

def recursive_remove(path: str) -> None:
    for name, props in ftp.mlsd(path):
        if name in (".", ".."):
            continue
        elif props["type"] == "file":
            ftp.delete(f"{path}/{name}")
        elif props["type"] == "dir":
            recursive_remove(f"{path}/{name}")
    ftp.rmd(path)

global_cfg = config["global"]
if global_cfg["purge_server"]:
    print("Purging the server root...")
    recursive_remove(global_cfg["server_root"])
    ftp.mkd(global_cfg["server_root"])
    print("  Successfully purged the server root")
ftp.cwd(global_cfg["server_root"])

root: Path = path / global_cfg["local_root"]
ignored: list[str] = []
for ignore in config["ignore"]["paths"]:
    ignore: Path = (root / ignore).resolve()
    ignored.append(str(ignore))

def check_ignored(path: str, dirs: list[str], files: list[str]) -> bool:
    for ignore in ignored:
        if ignore in path:
            dirs.clear()
            return True
    for i, file in enumerate(files):
        for ignore in ignored:
            if ignore in os.path.join(path, file):
                files.pop(i)
                break
    return False

print("Uploading files...")

for path, dirs, files in os.walk(root):
    path = os.path.normpath(path)
    if check_ignored(path, dirs, files): continue
    dir_path = os.path.relpath(path, root)

    if not dir_path in (".", ".."):
        print_path = dir_path.replace('\\', '/')
        print(f"Creating {print_path}")
        for dir_name in os.path.split(dir_path):
            if not dir_name: continue
            try:
                ftp.mkd(dir_name)
            except:
                pass
            ftp.cwd(dir_name)

    for filename in files:
        print(f"  Uploading {filename}")
        with open(os.path.join(path, filename), "rb") as file:
            ftp.storbinary(f"STOR {filename}", file)

    if not dir_path in (".", ".."):
        for dir_name in os.path.split(dir_path):
            if not dir_name: continue
            ftp.cwd("..")

end = time() - start
print_end = int(round(end, 3) * 1000)
print("Successful upload")
print(f"Total time elapsed: {print_end}ms")

ftp.quit()

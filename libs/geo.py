from os.path import exists
from typing import Union
import geoip2.database
import requests as r
from random import randint
from os import remove
import tarfile
from libs.config import geoIp2_token

db_name = None

print(f"Downloading geo-base...")
db_temp = r.get(f"https://download.maxmind.com/app/geoip_download",
                params={"edition_id": "GeoLite2-Country", "license_key": geoIp2_token, "suffix": "tar.gz"}).content

print("saving..")
tar_name = str(randint(1, 1000000))
open(tar_name, 'wb').write(db_temp)

print("Unpack..")
tar = tarfile.open(tar_name, "r:gz")
for file in tar:
    if file.name.endswith(".mmdb"):
        db_name = file.name
        if exists(db_name):
            remove(db_name)
        tar.extract(file)
        break
tar.close()

print("remove temp files..")
remove(tar_name)

print("Geo database ready!\n")

db = geoip2.database.Reader(db_name)


def get_country(ip: str) -> Union[None, str]:
    try:
        return db.country(ip).country.iso_code
    except:
        return None

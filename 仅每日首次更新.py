import os
import datetime

today = datetime.date.today().strftime("%Y-%m-%d")
file_name = "更新日志.ini"
run_2py = True

if os.path.exists(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if len(lines) > 0:
        last_line = lines[-1].strip()
        if last_line.startswith(today):
            run_2py = False

if run_2py:
    os.system("python 双击自动更新.py")

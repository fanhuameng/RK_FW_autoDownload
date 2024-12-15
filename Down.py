import logging
import os
import time
import yaml
import hashlib
import win32file
import sys
import select

logging.basicConfig(level=logging.INFO)

def is_used(file_name):
	try:
		vHandle = win32file.CreateFile(file_name, win32file.GENERIC_READ, 0, None, win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None)
		return int(vHandle) == win32file.INVALID_HANDLE_VALUE
	except:
		return True
	finally:
		try:
			win32file.CloseHandle(vHandle)
		except:
			pass
def def_config():
    data = {
        # 路径依赖
        "path": {
            "loader":       ".\\MiniLoaderAll.bin",
            "boot":         ".\\boot.img",
            "uboot":        ".\\uboot.img",
            "misc":         ".\\misc.img",
            "oem":          ".\\oem.img",
            "parameter":    ".\\parameter.txt",
            "recovery":     ".\\recovery.img",
            "rootfs":       ".\\rootfs.img",
            "update":       ".\\update.img",
            "userdata":     ".\\userdata.img"
        },
        # 是否检测变化
        "is_file_check": {
            "loader": True,
            "boot": True,
            "uboot": True,
            "misc": True,
            "oem": True,
            "parameter": True,
            "recovery": True,
            "rootfs": True,
            "update": True,
            "userdata": True
        },
        "upgrade_tool_path": ".\\upgrade_tool.exe"
    }
    return data

def load_config():
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
        return config

if "__main__" == __name__:
    sys.stdin.fileno()

    if not os.path.isfile("config.yaml"):
        with open("config.yaml", "w") as file:
            yaml.dump(def_config(), file)
    config = load_config()

    md5_dict = {}
    if not os.path.exists(config["path"]['loader']):
        logging.error(f"找不到 loader 文件 目录: {config['path']['loader']}")
        exit(0)
    n_cnt = 0
    check_all_flag = True
    while True and check_all_flag:
        logging.info("开始检测 ...")
        check_list = config["is_file_check"].keys()
        update_list = []
        for _ in check_list:
            if config["is_file_check"][_]:
                # 检查当前文件md5值
                if not os.path.exists(config["path"][_]):
                    print(f"未发现该文件 {_} 目录: {config['path'][_]}")
                    exit()
                while True:
                    if not is_used(config["path"][_]):
                        break
                    time.sleep(1)
                with open(config["path"][_], 'rb') as file:
                    data = file.read()
                    md5_hex = hashlib.md5(data).hexdigest()
                if md5_dict.get(_) == None:
                    # 未找到 更新一下
                    md5_dict.update({_: md5_hex})
                else:
                    if md5_hex != md5_dict.get(_):
                        # md5 不等于时需要更新器件
                        update_list.append(_)
                        logging.info(f"文件变更等待更新 {_}")
                        md5_dict.update({_: md5_hex})
                        update_list.append(_)
        time.sleep(1)
        if len(update_list) != 0:
            logging.info("更新开始")
            while True:
                cmd = f"{config['upgrade_tool_path']} ld"
                req = os.popen(cmd)
                req_dat = req.read()
                time.sleep(1)
                logging.info("检测中...")
                # 检测到设备
                if req_dat.find('DevNo') != -1:
                    logging.info("检测到设备")
                    cmd = f"{config['upgrade_tool_path']} db {config['path']['loader']}"
                    req = os.popen(cmd)
                    req_dat = req.read()
                    if req_dat.find('Download boot ok') == -1:
                        # 烧录失败
                        logging.error("下载 Download boot 失败")
                        break
                    else:
                        logging.info(f"下载boot 成功, 切换存储 ")
                        cmd = f"{config['upgrade_tool_path']} ssd 2"
                        req = os.popen(cmd)
                        req_dat = req.read()
                        if req_dat.find('Switch EMMC ok') == -1:
                            # 烧录失败
                            logging.error("Switch EMMC 失败")
                            break
                        else:
                            logging.info(f"开始烧录文件")
                        # 优先烧录 分区文件
                        if "parameter" in update_list:
                            cmd = f"{config['upgrade_tool_path']} di -p {config['path']['parameter']}"
                            req = os.popen(cmd)
                            req_dat = req.read()
                            if req_dat.find("Write gpt ok.") != -1:
                                logging.info("分区表 烧录正常")
                            else:
                                logging.info(f"分区表 烧录异常")
                                break
                            update_list.remove("parameter")
                        for _ in update_list:
                            logging.info(f"烧录 {_}")
                            cmd = f"{config['upgrade_tool_path']} di -{_} {config['path'][_]}"
                            req = os.popen(cmd)
                            req_dat = req.read()
                            if req_dat.find("Download image ok") != -1:
                                logging.info(f"{_} 烧录正常")
                            else:
                                logging.info(f"{_} 烧录异常")
                                exit()
                    logging.info("烧录完成 重启设备")
                    cmd = f"{config['upgrade_tool_path']} rd"
                    req = os.popen(cmd)
                    req_dat = req.read()
                    if req_dat.find("Reset Device OK") != -1:
                        logging.info(f"重启成功")
                    else:
                        logging.info(f"重启失败")
                    break
        n_cnt += 1
        logging.info(f"下轮检测 {n_cnt} 回车开始，按p重新加载配置")
        userInput = input()
        if userInput.find('p') != -1:
            logging.info("加载配置文件")
            config = load_config()

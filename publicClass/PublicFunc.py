#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import math
import traceback
import yaml
import asyncio
import subprocess
import hashlib
from flask import abort
from publicClass.Logger import Logger
from pathlib import Path
import paramiko
from publicClass.HttpFunc import get_file_func
from publicClass.HttpFunc import http_post
from jinja2 import Environment, FileSystemLoader


def read_yaml(file_path):
    """解析yaml文件
    使用PyYaml模块解析yaml文件成字段数据
    :return: yaml文件解析后的字典格式数据
    """
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def shell_cmd(log_type, str_cmd):
    logger = Logger(log_type)
    str_cmd = str_cmd.replace("//", "/")
    cmd = subprocess.Popen(str_cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    str_stdout = cmd.stdout.read().decode()
    cmd.stdout.close()
    str_stderr = cmd.stderr.read().decode()
    cmd.stderr.close()
    if str_stdout:
        logger.info("\n" + str_stdout)
    if str_stderr:
        logger.error("\n" + str_stderr)
        logger.error("报错退出...")
        return False
    return True


def ssh_shell_cmd(log_type, host, str_cmd):
    logger = Logger(log_type)
    str_cmd = str_cmd.replace("//", "/")
    private = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=22, username='root', pkey=private)
    logger.info("ssh已连接%s" % host)
    stdin, stdout, stderr = client.exec_command(str_cmd)
    str_stdout = stdout.read().decode()
    str_stderr = stderr.read().decode()
    if str_stderr:
        logger.error("\n" + str_stderr)
    client.close()
    logger.info("ssh断开连接%s" % host)
    return str_stdout


def is_compress(file_name):
    """判断压缩函数
    判断文件是否是压缩文件
    :param file_name: 文件名
    :return:
    """
    compress_extension = (".bz", ".xz", ".gz", ".zip", ".tar")
    filepath, tmp_filename = os.path.split(file_name)
    filename, extension = os.path.splitext(tmp_filename)
    if extension in compress_extension:
        return True
    else:
        return False


def j2_to_file(log_type, config, file_j2, file_yaml):
    logger = Logger(log_type)
    env = Environment(loader=FileSystemLoader('/'), trim_blocks=True, lstrip_blocks=True)
    try:
        template = env.get_template(file_j2)
        out = template.render(config)
        with open(file_yaml, "w", encoding="utf-8") as f:
            f.write(out)
        return True
    except Exception:
        logger.info("j2模板转换失败，报错如下")
        logger.error(traceback.format_exc())
        return False


def set_ns_svc(sys_name, app_name):
    service_name = "%s-%s" % (sys_name, app_name)
    namespace = "%s-system" % sys_name

    if app_name == "noApp":
        return namespace
    else:
        return service_name, namespace


def calculate_weight(weight_list, count):
    weight = []
    if not weight_list:
        if count == 1:
            weight = [100]
        else:
            average = math.ceil(100 / count)
            for i in range(1, count + 1):
                if i == count:
                    last_weight = 100 - (average * (count - 1))
                    weight.append(last_weight)
                else:
                    weight.append(average)
    else:
        weight = weight_list
    return weight


def get_remote_file(log_type, object_storage_conf, file_key, file_md5, file_full_name):
    logger = Logger(log_type)
    access_key = object_storage_conf['accessKey']
    server_url = object_storage_conf['serverUrl']
    client_ip = str(object_storage_conf['clientIp'])
    params = {
        "fileid": file_key,
        "accessKey": access_key,
        "clientIp": client_ip
    }
    asyncio.run(get_file_func(server_url, params, file_full_name))
    local_file = Path(file_full_name)
    if local_file.is_file():
        logger.info("文件%s下载成功" % file_full_name)
        with open(file_full_name, "rb") as f:
            current_md5 = hashlib.md5(f.read()).hexdigest()
            if file_md5 != current_md5:
                logger.error("文件%s下载失败,md5码不一致" % file_full_name)
                return False
            else:
                logger.info("文件%s比较md5码一致" % file_full_name)
    else:
        logger.error("文件%s下载失败" % file_full_name)
        return False
    return True


def get_files(file_dir, suffix):
    res = []
    # =>当前根,根下目录,目录下的文件
    for root, directory, files in os.walk(file_dir):
        for filename in files:
            # =>文件名,文件后缀
            name, suf = os.path.splitext(filename)
            if suf == suffix:
                # =>把一串字符串组合成路径
                res.append(os.path.join(root, filename))
    return res


def compared_version(ver1, ver2):
    """
    传入不带英文的版本号,特殊情况："10.12.2.6.5">"10.12.2.6"
    :param ver1: 版本号1
    :param ver2: 版本号2
    :return: ver1< = >ver2返回-1/0/1
    """
    list1 = str(ver1).split(".")
    list2 = str(ver2).split(".")
    print(list1)
    print(list2)
    # 循环次数为短的列表的len
    for i in range(len(list1)) if len(list1) < len(list2) else range(len(list2)):
        if int(list1[i]) == int(list2[i]):
            pass
        elif int(list1[i]) < int(list2[i]):
            return -1
        else:
            return 1
    # 循环结束，哪个列表长哪个版本号高
    if len(list1) == len(list2):
        return 0
    elif len(list1) < len(list2):
        return -1
    else:
        return 1


def send_state_back(task_back_url, task_flow_id, task_state, step_state, step_info):
    step_info = {
        'taskFlowId': task_flow_id,
        'taskState': str(task_state),
        'stepState': str(step_state),
        'stepInfo': step_info
    }
    asyncio.run(http_post(task_back_url, step_info))

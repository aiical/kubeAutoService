#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
from publicClass.Logger import Logger
import traceback


def check_json(post_json_data):
    status = 0
    result = ""
    if not post_json_data.__contains__('taskFlowId'):
        status += 1
        result = "%s&&json[taskFlowId]不存在" % result
    if not post_json_data.__contains__('para'):
        status += 1
        result = "%s&&json[para]不存在" % result
    else:
        if not post_json_data['para'].__contains__('global'):
            status += 1
            result = "%s&&json[para.global]不存在" % result

    task_flow_id = post_json_data['taskFlowId']
    para_data = post_json_data['para']
    resource_data = para_data['kube']


def exchange_json(para_data):
    logger = Logger("server")
    try:
        str_sys_name = para_data['global']['sysName']
        str_app_name = para_data['global']['appName']
        tmp_sys_name = str_sys_name.lower()
        tmp_app_name = str_app_name.lower()
        """转换runEnv"""
        str_run_env = para_data['global']['runEnv']
        tmp_run_env = str_run_env.lower()
        para_data['global'].update({
            'runEnv': str(tmp_run_env),
            'sysName': str(tmp_sys_name),
            'appName': str(tmp_app_name)
        })
        """转换appContext"""
        str_app_context = para_data['global']['appContext']
        # tmp_app_context = eval(str_app_context)
        tmp_app_context = str_app_context

        text_context = tmp_app_context['appContext']
        para_data['global'].update({
            'appContext': text_context
        })
        return para_data
    except (KeyError, NameError):
        logger.error(traceback.format_exc())
        return 1


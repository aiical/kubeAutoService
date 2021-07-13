#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import json
import traceback
from publicClass.Logger import Logger
from publicClass.JsonCheck import exchange_json
from publicClass.PublicFunc import send_state_back


class InitProject:
    def __init__(self, settings_conf, info):
        self.logger = Logger("server")
        self.info = info
        self.settings_conf = settings_conf
        try:
            self.task_back_url = self.settings_conf['taskInfoBack']['url']
            self.task_flow_id = self.info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
        self.para_config = None

    def check(self):
        self.logger.info("接收服务操作json数据:'%r'" % self.info)
        try:
            tmp_post_json_data = json.loads(self.info['para'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1
        self.logger.info("转换前json数据:'%r'" % tmp_post_json_data)
        self.para_config = exchange_json(tmp_post_json_data)
        if isinstance(self.para_config, int) and self.para_config == 1:
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "(init)：发布json预处理失败")
            self.logger.error("发布json预处理失败")
            self.logger.error("错误退出程序")
            return 1
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "(init)：发布json预处理成功")
        self.logger.info("转换后json数据:'%r'" % self.para_config)
        return 0

    def deploy(self):
        pass

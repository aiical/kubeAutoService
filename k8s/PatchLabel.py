#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import asyncio
import traceback
from flask import abort
from k8s.InitProject import InitProject
from publicClass.PublicFunc import send_state_back
from publicClass.HttpFunc import k8s_api_http_patch


class PatchLabel(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)

    def deploy(self):
        try:
            api_server = "https://%s:%s" % (
                str(self.settings_conf['apiServer']['host']), str(self.settings_conf['apiServer']['port']))
            token = self.settings_conf['connectInfo']['token']
            global_config = self.info['para']['global']

            label_list = global_config['labels']
            if not label_list:
                self.logger.error("接收json缺少label标签绑定关系信息")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：接收json缺少label标签绑定关系信息")
                abort(404)

        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            error_num = 0
            for label in label_list:
                # pk_id = "未知主键"
                if label.__contains__('pkId'):
                    pk_id = label['pkId']
                else:
                    self.logger.error("该条labels字典中不存在pkId键")
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 5,
                                    "[ERROR]：该条labels字典中不存在pkId键")
                    continue
                try:
                    label_name = label['labelName']
                    label_value = label['labelValue']
                    node_ip = label['nodeIp']
                    opera_type = str(label['type'])
                    url = "%s/api/v1/nodes/%s" % (api_server, str(node_ip))
                except(KeyError, NameError):
                    self.logger.error(traceback.format_exc())
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 5,
                                    "[ERROR]：主键%s对应字典数据解析有误，具体报错：%s" % (pk_id, traceback.format_exc()))
                    error_num += 1
                    # abort(404)
                else:
                    if opera_type == "0":
                        patch_data = '[{"op": "add", "path": "/metadata/labels/%s", "value": "%s"}]' % (
                            label_name, label_value)
                    else:
                        patch_data = '[{"op": "remove", "path": "/metadata/labels/%s"}]' % label_name
                    patch_code, patch_json = asyncio.run(
                        k8s_api_http_patch(url, token, patch_data))
                    if patch_code == 200:
                        if opera_type == "1":
                            opera_text = "添加"
                        else:
                            opera_text = "删除"

                        self.logger.info("节点%s上%s标签[%s: %s](主键：%s)成功" % (
                            str(node_ip), opera_text, label_name, label_value, pk_id))
                        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                        "[INFO]：节点%s上%s标签[%s: %s](主键：%s)成功" % (
                                            str(node_ip), opera_text, label_name, label_value, pk_id))
                    else:
                        fail_msg = "未知错误"
                        if patch_json.__contains__('message'):
                            fail_msg = patch_json['message']
                        if opera_type == "0":
                            opera_text = "添加"
                        else:
                            opera_text = "删除"

                        self.logger.error("节点%s上%s标签[%s: %s](主键：%s)失败，失败码为%s，失败原因：%s" % (
                            str(node_ip), opera_text, label_name, label_value, pk_id, patch_code, fail_msg))

                        send_state_back(self.task_back_url, self.task_flow_id, 2, 5,
                                        "[ERROR]：节点%s上%s标签[%s: %s](主键：%s)失败，失败码为%s，失败原因：%s" % (
                                            str(node_ip), opera_text, label_name, label_value,
                                            pk_id, patch_code, fail_msg
                                            )
                                        )
                        error_num += 1
                        # abort(404)
            if error_num == 0:
                self.logger.info("节点标签绑定关系同步完成")
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "[FINISH]：节点标签绑定关系同步完成")
            else:
                self.logger.warn("节点标签绑定关系同步部分异常，存在不成功记录")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[FINISH WITH ERROR]：节点标签绑定关系同步异常，存在不成功记录")

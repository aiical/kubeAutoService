#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import asyncio
import traceback
from flask import abort
from k8s.InitProject import InitProject
from k8s.CheckOpera import CheckOpera
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
            opera_type = self.info['operaType']
            node_list = global_config['nodes']
            if not node_list:
                self.logger.error("接收json缺少node节点信息")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：接收json缺少node节点信息")
                abort(404)
            label_list = global_config['nodes']
            if not label_list:
                self.logger.error("接收json缺少label标签信息")
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：接收json缺少label标签信息")
                abort(404)

        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            for node in node_list:
                url = "%s/api/v1/nodes/%s" % (api_server, str(node))
                # check_state = CheckOpera(self.settings_conf)
                # check_result = check_state.get_node_status(url, "node")
                # try:
                #     exist_label_list = check_result['labels']
                # except(KeyError, NameError):
                #     self.logger.error(traceback.format_exc())
                #     send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                #                     "[ERROR]：%s" % traceback.format_exc())
                #     abort(404)
                # else:
                for label in label_list:
                    try:
                        label_name = label['name']
                        label_value = label['value']
                        # if exist_label_list.__contains__(label_name):
                        #     exist_label_value = exist_label_list[label_name]
                        #     if exist_label_value == label_value:
                        #         self.logger.warn("节点%s上已存在标签[%s: %s]，跳过" % (
                        #             str(node), label_name, label_value))
                        #         send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        #                         "[WARN]：节点%s上已存在标签[%s: %s]，跳过" % (
                        #                             str(node), label_name, label_value))
                        #         continue
                        #     else:
                        #         self.logger.error("节点%s上已存在key为%s的标签，但value不同，[旧：%s；新：%s]" % (
                        #             str(node), label_name, exist_label_value, label_value))
                        #         send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        #                         "[WARN]：节点%s上已存在key为%s的标签，但value不同，[旧：%s；新：%s],已覆盖为新标签值" % (
                        #                             str(node), label_name, exist_label_value, label_value))
                    except(KeyError, NameError):
                        self.logger.error(traceback.format_exc())
                        send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                        "[ERROR]：%s" % traceback.format_exc())
                        abort(404)
                    else:
                        if opera_type == "7":
                            patch_data = '[{"op": "add", "path": "/metadata/labels/%s", "value": "%s"}]' % (
                                label_name, label_value)
                        elif opera_type == "8":
                            patch_data = '[{"op": "remove", "path": "/metadata/labels/%s"}]' % label_name
                        patch_code, patch_json = asyncio.run(
                            k8s_api_http_patch(url, token, patch_data))
                        if patch_code == 200:
                            if opera_type == "add":
                                opera_text = "添加"
                            else:
                                opera_text = "删除"

                            self.logger.info("节点%s上%s标签[%s: %s]成功" % (
                                str(node), opera_text, label_name, label_value))
                            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                            "[INFO]：节点%s上%s标签[%s: %s]成功" % (
                                                str(node), opera_text, label_name, label_value))
                        else:
                            try:
                                fail_msg = patch_json['message']
                            except(KeyError, NameError):
                                self.logger.error(traceback.format_exc())
                                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                                "[ERROR]：%s" % traceback.format_exc())
                                abort(404)
                            else:
                                if opera_type == "add":
                                    opera_text = "添加"
                                else:
                                    opera_text = "删除"

                                self.logger.error("节点%s上%s标签[%s: %s]失败，失败码为%s" % (
                                    str(node), opera_text, label_name, label_value, patch_code))
                                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                                "[ERROR]：节点%s上%s标签[%s: %s]失败，失败码为%s，失败原因：%s" % (
                                                    str(node), opera_text, label_name, label_value, patch_code, fail_msg
                                                    )
                                                )
                                abort(404)

            self.logger.info("节点标签添加完成")
            send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                            "[INFO]：节点标签添加完成")

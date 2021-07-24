#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import traceback
from flask import abort
from k8s.InitProject import InitProject
from publicClass.PublicFunc import send_state_back
from k8s.AuthorizationPolicy import AuthorizationPolicy


class InitPolicy(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)

    def deploy(self):
        try:
            sys_base_path = self.settings_conf['pathInfo']['deployBasePath']
            global_config = self.para_config['global']
            mode = global_config['mode']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            policy_path = "%s/policyFile" % sys_base_path
            policy_path = policy_path.replace("//", "/")
            if not os.path.exists(policy_path):
                os.makedirs(policy_path)
            policy_deploy = AuthorizationPolicy(None, global_config, policy_path)

            policy_info = policy_deploy.get_ap_svc_to_svc_info()
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "[INFO]：获取AuthorizationPolicy信息成功")
            self.logger.info("获取AuthorizationPolicy信息成功")
            if mode == "add":
                policy_name = policy_deploy.create_svc_to_svc_yaml(policy_info)
                send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                "[INFO]：创建AuthorizationPolicy.yaml成功")
                self.logger.info("创建AuthorizationPolicy.yaml成功")
                policy_deploy.deploy_svc_to_svc(policy_name)
                send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                "[INFO]：部署AuthorizationPolicy策略成功")
                self.logger.info("部署AuthorizationPolicy策略成功")
            else:
                policy_deploy.delete_svc_to_svc(policy_info)
                send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                "[INFO]：卸载AuthorizationPolicy策略成功")
                self.logger.info("卸载AuthorizationPolicy策略成功")

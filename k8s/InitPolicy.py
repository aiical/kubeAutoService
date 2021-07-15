#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import traceback
from publicClass.Logger import Logger
import os
from k8s.InitProject import InitProject
from publicClass.PublicFunc import send_state_back
from k8s.AuthorizationPolicy import AuthorizationPolicy


class InitPolicy(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)

    def deploy(self):

        current_task_step = 0
        sys_base_path = self.settings_conf['pathInfo']['deployBasePath']
        global_config = self.para_config['global']
        mode = global_config['mode']
        if mode == "add":
            total_task_steps = 3
        else:
            total_task_steps = 2

        policy_path = "%s/policyFile" % sys_base_path
        policy_path = policy_path.replace("//", "/")
        if not os.path.exists(policy_path):
            os.makedirs(policy_path)
        policy_deploy = AuthorizationPolicy(None, global_config, policy_path)

        policy_info = policy_deploy.get_ap_svc_to_svc_info()
        current_task_step += 1
        if isinstance(policy_info, int) and policy_info == 1:
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "(%s/%s)：获取AuthorizationPolicy信息失败" % (str(current_task_step), str(total_task_steps)))
            self.logger.error("获取AuthorizationPolicy信息失败")
            self.logger.error("错误退出程序")
            return 1
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "(%s/%s)：获取AuthorizationPolicy信息成功" % (str(current_task_step), str(total_task_steps)))
        self.logger.info("获取AuthorizationPolicy信息成功")
        if mode == "add":
            current_task_step += 1
            policy_name = policy_deploy.create_svc_to_svc_yaml(policy_info)
            if isinstance(policy_name, int) and policy_info == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：创建AuthorizationPolicy.yaml失败" %
                                (str(current_task_step), str(total_task_steps)))
                self.logger.error("创建AuthorizationPolicy.yaml失败")
                self.logger.error("错误退出程序")
                return 1
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：创建AuthorizationPolicy.yaml成功" % (str(current_task_step), str(total_task_steps)))
            self.logger.info("创建AuthorizationPolicy.yaml成功")
            current_task_step += 1
            code = policy_deploy.deploy_svc_to_svc(policy_name)
            if code == "1":
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：部署AuthorizationPolicy策略失败"
                                % (str(current_task_step), str(total_task_steps)))
                self.logger.error("部署AuthorizationPolicy策略失败" % policy_name)
                self.logger.error("错误退出程序")
                return 1
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：部署AuthorizationPolicy策略成功" % (str(current_task_step), str(total_task_steps)))
            self.logger.info("部署AuthorizationPolicy策略成功")
        else:
            current_task_step += 1
            code = policy_deploy.delete_svc_to_svc(policy_info)
            if code == "1":
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：卸载AuthorizationPolicy策略失败"
                                % (str(current_task_step), str(total_task_steps)))
                self.logger.error("卸载AuthorizationPolicy策略失败")
                self.logger.error("错误退出程序")
                return 1
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：卸载AuthorizationPolicy策略成功" % (str(current_task_step), str(total_task_steps)))
            self.logger.info("卸载AuthorizationPolicy策略成功")

        return 0

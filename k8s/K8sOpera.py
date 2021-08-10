#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import time
import os
import traceback
from flask import abort
from publicClass.Logger import Logger
from publicClass.PublicFunc import shell_cmd, set_ns_svc, get_files, send_state_back, file_replace
from k8s.Service import Service
from k8s.ServiceAccount import ServiceAccount
from k8s.Deployment import Deployment
from k8s.StatefulSet import StatefulSet
from k8s.ConfigMap import ConfigMap
from k8s.Gateway import Gateway
from k8s.DestinationRule import DestinationRule
from k8s.VirtualService import VirtualService
from k8s.AuthorizationPolicy import AuthorizationPolicy
from k8s.Job import Job
from k8s.Cronjob import CronJob


class K8sOpera:
    def __init__(self, settings_conf, global_info, k8s_info):
        self.global_info = global_info
        self.k8s_info = k8s_info
        self.logger = Logger("server")
        """读取settings设置"""
        self.setting_conf = settings_conf

        try:
            self.task_back_url = self.global_info['taskBackUrl']
            self.task_flow_id = self.global_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            abort(404)
        else:
            try:
                """生产k8s yaml文件存放地址"""
                self.sys_name = self.global_info['sysName']
                self.app_name = self.global_info['appName']
                self.dc_name = self.global_info['dcName']
                self.app_context = self.global_info['appContext']
                k8s_base_path = self.setting_conf['pathInfo']['deployBasePath']
            except(KeyError, NameError):
                self.logger.error(traceback.format_exc())
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：%s" % traceback.format_exc())
                abort(404)
            else:
                """获取服务名和名称空间"""
                self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)

                self.k8s_path = "%s/%s/%s/YamlFile" % (k8s_base_path, self.sys_name, self.service_name)
                self.k8s_path = self.k8s_path.replace("//", "/")

                """备份k8s yaml目录
                YamlFile_yyyymmddHh24miss
                """
                logger = Logger("server")
                dir_bak_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
                self.k8s_bak_path = self.k8s_path + '_' + dir_bak_time

                self.k8s_ori_yaml_file = []
                if os.path.exists(self.k8s_path):
                    self.k8s_ori_yaml_file = get_files(self.k8s_path, '.yaml')
                    str_cmd = "mv %s %s" % (self.k8s_path, self.k8s_bak_path)
                    logger.info("备份目录%s到%s" % (self.k8s_path, self.k8s_bak_path))
                    logger.info("COMMAND: %s" % str_cmd)
                    if not shell_cmd("server", str_cmd):
                        send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                        "[ERROR]:COMMAND:%s执行出错" % str_cmd)
                        abort(404)

                    start_file = "%s/appStart.sh" % self.k8s_bak_path
                    file_replace(start_file, self.k8s_path, self.k8s_bak_path)
                    logger.info("修改备份目录下%s中文件目录从%s到%s" % (start_file, self.k8s_path, self.k8s_bak_path))

                os.makedirs(self.k8s_path)

                """介质源路径"""
                self.media_src_path = "%s/%s/%s/ConfigMapMedia" % (k8s_base_path, self.sys_name, self.service_name)
                self.media_src_path = self.media_src_path.replace("//", "/")
                if not os.path.exists(self.media_src_path):
                    os.makedirs(self.media_src_path)

    def create_resource_yaml(self):
        start_command_list = []
        try:
            announce_type = self.k8s_info['announceType']
            controller_type = self.k8s_info['controllerType']
            server_type = self.k8s_info['serverType']['type']
            file_beat_flag = self.global_info['fileBeatFlag']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
            """生成config.yaml"""
            self.logger.info("生成k8s资源清单config.yaml")
            config_map = ConfigMap(
                self.setting_conf, self.global_info, self.k8s_info, self.k8s_path, self.media_src_path)

            if file_beat_flag == "Y":
                cm_file_beat = config_map.get_config_map_file_beat_info()
                start_command_list.extend(config_map.create_config_map_file_beat_yaml(cm_file_beat))
            cm_app = config_map.get_config_map_app_info()
            start_command_list.extend(config_map.create_config_map_app_yaml(cm_app))
            if announce_type == "once":
                """生成job.yaml"""
                self.logger.info("生成k8s资源清单job.yaml")
                job = Job(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                job_list = job.get_job_info()
                start_command_list.extend(job.create_job_yaml(job_list))
            elif announce_type == "timed":
                """生成cronJob.yaml"""
                self.logger.info("生成k8s资源清单cronJob.yaml")
                cronjob = CronJob(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                cronjob_list = cronjob.get_cron_job_info()
                start_command_list.extend(cronjob.create_cron_job_yaml(cronjob_list))
            elif announce_type == "permanent":
                """生成serviceAccount.yaml"""
                self.logger.info("生成k8s资源清单serviceaccount.yaml")
                service_account = ServiceAccount(self.global_info, self.k8s_info, self.k8s_path)
                service_account_info = service_account.get_service_account_info()
                tmp_command = service_account.create_service_account_yaml(service_account_info)
                start_command_list.extend(tmp_command)
                """生成service.yaml"""
                self.logger.info("生成k8s资源清单service.yaml")
                service = Service(self.global_info, self.k8s_info, self.k8s_path)
                service_info = service.get_service_info()
                tmp_command = service.create_service_yaml(service_info, "N")
                start_command_list.extend(tmp_command)
                if controller_type == "stateless":
                    """生成deployment.yaml"""
                    self.logger.info("生成k8s资源清单deployment.yaml")
                    deployment = Deployment(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                    deployment_list = deployment.get_deployment_info()
                    tmp_command = deployment.create_deployment_yaml(deployment_list)
                    start_command_list.extend(tmp_command)
                elif controller_type == "stateful":
                    """生成statefulSet.yaml"""
                    self.logger.info("生成k8s资源清单statefulSet.yaml")
                    stateful_set = StatefulSet(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                    stateful_set_list = stateful_set.get_stateful_set_info()
                    tmp_command = stateful_set.create_stateful_set_yaml(stateful_set_list)
                    start_command_list.extend(tmp_command)

                    """生成service-headless.yaml"""
                    self.logger.info("生成k8s资源清单service-headless.yaml")
                    tmp_command = service.create_service_yaml(service_info, "Y")
                    start_command_list.extend(tmp_command)

                if server_type == "istio":
                    """生成gateway.yaml"""
                    self.logger.info("生成k8s资源清单gateway.yaml")
                    gateway = Gateway(self.global_info, self.k8s_info, self.k8s_path)
                    gateway_info = gateway.get_gateway_info()
                    tmp_command = gateway.create_gateway_yaml(gateway_info)
                    start_command_list.extend(tmp_command)
                    # if controller_type == "deployment":
                    """生成destinationRule.yaml"""
                    self.logger.info("生成k8s资源清单destinationRule.yaml")
                    destination_rule = DestinationRule(self.global_info, self.k8s_info, self.k8s_path)
                    destination_rule_info = destination_rule.get_destination_rule_info()
                    tmp_command = destination_rule.create_destination_rule_yaml(destination_rule_info)
                    start_command_list.extend(tmp_command)

                    """生成virtualService.yaml"""
                    self.logger.info("生成k8s资源清单virtualService.yaml")
                    virtual_service = VirtualService(self.global_info, self.k8s_info, self.k8s_path)
                    virtual_service_info = virtual_service.get_virtual_service_info()
                    tmp_command = virtual_service.create_virtual_service_yaml(virtual_service_info)
                    start_command_list.extend(tmp_command)

                    """生成authorizationPolicy.yaml"""
                    self.logger.info("生成k8s资源清单authorizationPolicy.yaml")
                    policy = AuthorizationPolicy(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                    dft_ns_policy_info = policy.get_ap_ns_to_svc_info()
                    tmp_dft_ns_command = policy.create_ns_to_svc_yaml(dft_ns_policy_info)
                    start_command_list.extend(tmp_dft_ns_command)
                    svc_policy_info_list = policy.get_ap_svc_to_svc_info()
                    if svc_policy_info_list:
                        for svc_policy_info in svc_policy_info_list:
                            tmp_svc_command = policy.create_svc_to_svc_yaml(svc_policy_info)
                            start_command_list.extend(tmp_svc_command)

                self.logger.info("启动服务命令列表如下")
                self.logger.info(start_command_list)

            k8s_current_yaml_file = get_files(self.k8s_path, '.yaml')
            k8s_del_yaml_file = [x for x in self.k8s_ori_yaml_file if x not in k8s_current_yaml_file]
            """生成appStart.sh"""
            self.logger.info("生成appStart.sh")
            with open(self.k8s_path + '/appStart.sh', "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n")
                """逐行执行部署命令"""
                for line in start_command_list:
                    """测试只生成不执行"""
                    # shell_cmd(line)
                    f.write("%s\n" % line)

            self.logger.info("生成deleteNoNeedYaml.sh")
            if k8s_del_yaml_file:
                self.logger.info("生成deleteNoNeedYaml.sh记录较上次发布多余资源")
                with open(self.k8s_path + '/deleteNoNeedYaml.sh', "w", encoding="utf-8") as f:
                    f.write("#!/bin/bash\n")
                    for del_file in k8s_del_yaml_file:
                        del_line = "kubectl delete -f %s" % del_file
                        del_line = del_line.replace(self.k8s_path, self.k8s_bak_path)
                        f.write("%s\n" % del_line)

    # def start_app(self, k8s_del_yaml_file):
    #     logger = Logger("server")
    #     logger.info("执行appStart.sh部署应用")
    #     code = shell_cmd("server", 'sh %s/appStart.sh' % self.k8s_path)
    #
    #     if k8s_del_yaml_file:
    #         logger.info("卸载较上次发布多余资源")
    #         for del_file in k8s_del_yaml_file:
    #             cmd_line = "kubectl delete -f %s" % del_file
    #             cmd_line = cmd_line.replace(self.k8s_path, self.k8s_bak_path)
    #             code = code or shell_cmd("server", cmd_line)
    #     return code

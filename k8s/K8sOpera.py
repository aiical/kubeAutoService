#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import time
import os
from publicClass.Logger import Logger
from publicClass.PublicFunc import shell_cmd, set_ns_svc, get_files
from k8s.Service import Service
from k8s.ServiceAccount import ServiceAccount
from k8s.Deployment import Deployment
from k8s.StatefulSet import StatefulSet
from k8s.ConfigMap import ConfigMap
from k8s.Gateway import Gateway
from k8s.DestinationRule import DestinationRule
from k8s.VirtualService import VirtualService
from k8s.Job import Job
from k8s.Cronjob import CronJob


class K8sOpera:
    def __init__(self, settings_conf, global_info, k8s_info):
        self.global_info = global_info
        self.k8s_info = k8s_info

        """读取settings设置"""
        self.setting_conf = settings_conf

        """生产k8s yaml文件存放地址"""
        # self.run_env = self.global_info['runEnv']
        self.sys_name = self.global_info['sysName']
        self.app_name = self.global_info['appName']
        self.dc_name = self.global_info['dcName']
        self.app_context = self.global_info['appContext']
        """获取服务名和名称空间"""
        self.service_name, self.namespace = set_ns_svc(self.sys_name, self.app_name)
        k8s_base_path = self.setting_conf['pathInfo']['deployBasePath']
        self.k8s_path = "%s/%s/%s/YamlFile" % (k8s_base_path, self.sys_name, self.service_name)
        # self.nginx_path = "%s/%s/%s/NginxFile" % (k8s_base_path, self.sys_name, self.service_name)
        self.k8s_path = self.k8s_path.replace("//", "/")
        # self.nginx_path = self.nginx_path.replace("//", "/")

        """备份k8s yaml目录
        YamlFile_yyyymmddHh24miss
        """
        logger = Logger("server")
        dir_bak_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        self.k8s_bak_path = self.k8s_path + '_' + dir_bak_time
        # nginx_bak_path = self.nginx_path + '_' + dir_bak_time

        self.k8s_ori_yaml_file = []
        if os.path.exists(self.k8s_path):
            self.k8s_ori_yaml_file = get_files(self.k8s_path, '.yaml')
            str_cmd = "mv %s %s" % (self.k8s_path, self.k8s_bak_path)
            logger.info("备份目录%s到%s" % (self.k8s_path, self.k8s_bak_path))
            logger.info("COMMAND: %s" % str_cmd)
            shell_cmd("server", str_cmd)
        os.makedirs(self.k8s_path)

        """介质源路径"""
        self.media_src_path = "%s/%s/%s/ConfigMapMedia" % (k8s_base_path, self.sys_name, self.service_name)
        self.media_src_path = self.media_src_path.replace("//", "/")
        if not os.path.exists(self.media_src_path):
            os.makedirs(self.media_src_path)

    def create_resource_yaml(self):
        logger = Logger("server")
        start_command_list = []
        announce_type = self.k8s_info['announceType']
        controller_type = self.k8s_info['controllerType']
        server_type = self.k8s_info['serverType']['type']
        """生成config.yaml"""
        logger.info("生成k8s资源清单config.yaml")
        config_map = ConfigMap(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path, self.media_src_path)
        file_beat_flag = self.global_info['fileBeatFlag']
        if file_beat_flag == "Y":
            cm_file_beat = config_map.get_config_map_file_beat_info()
            start_command_list.extend(config_map.create_config_map_file_beat_yaml(cm_file_beat))
        cm_app = config_map.get_config_map_app_info()
        if cm_app == 1:
            return 1
        start_command_list.extend(config_map.create_config_map_app_yaml(cm_app))
        if announce_type == "once":
            """生成job.yaml"""
            logger.info("生成k8s资源清单job.yaml")
            job = Job(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
            job_list = job.get_job_info()
            start_command_list.extend(job.create_job_yaml(job_list))
        elif announce_type == "timed":
            """生成cronjob.yaml"""
            logger.info("生成k8s资源清单cronjob.yaml")
            cronjob = CronJob(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
            cronjob_list = cronjob.get_cronjob_info()
            start_command_list.extend(cronjob.create_cronjob_yaml(cronjob_list))
        elif announce_type == "permanent":
            """生成serviceaccount.yaml"""
            logger.info("生成k8s资源清单serviceaccount.yaml")
            service_account = ServiceAccount(self.global_info, self.k8s_info, self.k8s_path)
            service_account_info = service_account.get_service_account_info()
            start_command_list.extend(service_account.create_service_account_yaml(service_account_info))
            """生成service.yaml"""
            logger.info("生成k8s资源清单service.yaml")
            service = Service(self.global_info, self.k8s_info, self.k8s_path)
            service_info = service.get_service_info()
            start_command_list.extend(service.create_service_yaml(service_info))
            if controller_type == "stateless":
                """生成deployment.yaml"""
                logger.info("生成k8s资源清单deployment.yaml")
                deployment = Deployment(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                deployment_list = deployment.get_deployment_info()
                start_command_list.extend(deployment.create_deployment_yaml(deployment_list))
            elif controller_type == "stateful":
                """生成statefulset.yaml"""
                logger.info("生成k8s资源清单statefulset.yaml")
                statefulset = StatefulSet(self.setting_conf, self.global_info, self.k8s_info, self.k8s_path)
                statefulset_list = statefulset.get_statefulset_info()
                start_command_list.extend(statefulset.create_statefulset_yaml(statefulset_list))

                service_info.update({
                    'ifHeadless': "Y"
                })
                start_command_list.extend(service.create_service_yaml(service_info))

            if server_type == "istio":
                """生成gateway.yaml"""
                logger.info("生成k8s资源清单gateway.yaml")
                gateway = Gateway(self.global_info, self.k8s_info, self.k8s_path)
                gateway_info = gateway.get_gateway_info()
                start_command_list.extend(gateway.create_gateway_yaml(gateway_info))
                # if controller_type == "deployment":
                """生成destinationrule.yaml"""
                logger.info("生成k8s资源清单destinationrule.yaml")
                destination_rule = DestinationRule(self.global_info, self.k8s_info, self.k8s_path)
                destination_rule_info = destination_rule.get_destination_rule_info()
                start_command_list.extend(destination_rule.create_destination_rule_yaml(destination_rule_info))

                """生成virtualservice.yaml"""
                logger.info("生成k8s资源清单virtualservice.yaml")
                virtual_service = VirtualService(self.global_info, self.k8s_info, self.k8s_path)
                virtual_service_info = virtual_service.get_virtual_service_info()
                start_command_list.extend(virtual_service.create_virtual_service_yaml(virtual_service_info))

            logger.info("启动服务命令列表如下")
            logger.info(start_command_list)

        k8s_current_yaml_file = get_files(self.k8s_path, '.yaml')
        k8s_del_yaml_file = [x for x in self.k8s_ori_yaml_file if x not in k8s_current_yaml_file]
        """生成appStart.sh"""
        logger.info("生成appStart.sh")
        with open(self.k8s_path + '/appStart.sh', "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            """逐行执行部署命令"""
            for line in start_command_list:
                """测试只生成不执行"""
                # shell_cmd(line)
                f.write("%s\n" % line)

        logger.info("生成deleteNoNeedYaml.sh")
        if k8s_del_yaml_file:
            logger.info("生成deleteNoNeedYaml.sh记录较上次发布多余资源")
            with open(self.k8s_path + '/deleteNoNeedYaml.sh', "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n")
                for del_file in k8s_del_yaml_file:
                    del_line = "kubectl delete -f %s" % del_file
                    del_line = del_line.replace(self.k8s_path, self.k8s_bak_path)
                    f.write("%s\n" % del_line)
        return 0

    def start_app(self, k8s_del_yaml_file):
        logger = Logger("server")
        logger.info("执行appStart.sh部署应用")
        code = shell_cmd("server", 'sh %s/appStart.sh' % self.k8s_path)

        if k8s_del_yaml_file:
            logger.info("卸载较上次发布多余资源")
            for del_file in k8s_del_yaml_file:
                cmd_line = "kubectl delete -f %s" % del_file
                cmd_line = cmd_line.replace(self.k8s_path, self.k8s_bak_path)
                code = code or shell_cmd("server", cmd_line)
        return code

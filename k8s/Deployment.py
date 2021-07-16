#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
import copy
from k8s.Controller import Controller
from publicClass.PublicFunc import j2_to_file


class Deployment(Controller):
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        Controller.__init__(self, settings_conf, global_info, k8s_info, k8s_path)

    def get_deployment_info(self):
        self.logger.info("开始获取deployment信息")
        deployment_list = []
        Controller.get_controller_share_info(self)
        Controller.get_volume_info(self, "stateless")
        Controller.get_pod_live_info(self)
        Controller.get_if_istio_ip(self)
        """获取版本个数"""
        version_count = int(self.k8s_info['versionCount'])
        cnt_range = int(version_count + 1)
        for i in range(1, cnt_range):
            version = "v%s" % str(i)
            self.controller_info.update({
                'version': version
            })
            """此处对列表中的某个字典做update，会导致所有字典的值都被覆盖，需要用到copy模块的深拷贝来解决copy.deepcopy"""
            deployment_list.append(copy.deepcopy(self.controller_info))
        self.logger.info("获取deployment信息完成")
        return deployment_list

    def create_deployment_yaml(self, deployment_list):
        apply_command_list = []
        for deployment_info in deployment_list:
            version = deployment_info["version"]
            server_type = deployment_info['serverType']
            self.logger.info("开始创建deployment-%s.yaml" % version)
            self.logger.info("deployment-%s配置如下：" % version)
            self.logger.info(deployment_info)
            deployment_yaml_j2 = '%s/templates/k8s/deployment.yaml.j2' % sys.path[0]
            deployment_yaml = '%s/deployment-%s.yaml' % (self.k8s_path, version)
            code = j2_to_file("server", deployment_info, deployment_yaml_j2, deployment_yaml)
            if code == 1:
                return code
            self.logger.info("deployment-%s.yaml已生成。" % version)
            if server_type == "istio":
                command = "istioctl kube-inject -f %s | kubectl apply -f -" % deployment_yaml
            else:
                command = "kubectl apply -f %s" % deployment_yaml
            apply_command_list.append(command)
        return apply_command_list

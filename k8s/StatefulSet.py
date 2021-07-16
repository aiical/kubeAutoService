#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from k8s.Controller import Controller
from publicClass.PublicFunc import j2_to_file


class StatefulSet(Controller):
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        Controller.__init__(self, settings_conf, global_info, k8s_info, k8s_path)

    def get_stateful_set_info(self):
        self.logger.info("开始获取statefulSet信息")
        Controller.get_controller_share_info(self)
        Controller.get_volume_info(self, "stateful")
        Controller.get_pod_live_info(self)
        Controller.get_if_istio_ip(self)
        self.logger.info("获取statefulSet信息完成")
        return self.controller_info

    def create_stateful_set_yaml(self, stateful_set_info):
        apply_command_list = []
        server_type = stateful_set_info['serverType']
        self.logger.info("开始创建statefulSet.yaml")
        self.logger.info("statefulSet配置如下：")
        self.logger.info(stateful_set_info)
        stateful_set_yaml_j2 = '%s/templates/k8s/statefulSet.yaml.j2' % sys.path[0]
        stateful_set_yaml = '%s/statefulSet.yaml' % self.k8s_path
        code = j2_to_file("server", stateful_set_info, stateful_set_yaml_j2, stateful_set_yaml)
        if code == 1:
            return code
        self.logger.info("statefulSet.yaml已生成。")
        if server_type == "istio":
            command = "istioctl kube-inject -f %s | kubectl apply -f -" % stateful_set_yaml
        else:
            command = "kubectl apply -f %s" % stateful_set_yaml
        apply_command_list.append(command)
        return apply_command_list

#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from k8s.Controller import Controller
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class Job(Controller):
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        Controller.__init__(self, settings_conf, global_info, k8s_info, k8s_path)

    def get_job_info(self):
        self.logger.info("开始获取job信息")
        Controller.get_controller_share_info(self)
        Controller.get_volume_info(self, "job")
        self.logger.info("获取job信息完成")
        return self.controller_info

    def create_job_yaml(self, job_info):
        self.logger.info("开始创建job.yaml")
        self.logger.info("job配置如下：")
        self.logger.info(job_info)
        job_yaml_j2 = '%s/templates/k8s/job.yaml.j2' % sys.path[0]
        job_yaml = '%s/job.yaml' % self.k8s_path

        j2_to_file("server", job_info, job_yaml_j2, job_yaml)
        self.logger.info("job.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % job_yaml]
        return apply_command_list

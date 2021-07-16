#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import sys
from k8s.Controller import Controller
from publicClass.PublicFunc import j2_to_file, set_ns_svc


class CronJob(Controller):
    def __init__(self, settings_conf, global_info, k8s_info, k8s_path):
        Controller.__init__(self, settings_conf, global_info, k8s_info, k8s_path)
        
    def get_cron_job_info(self):
        self.logger.info("开始获取cronJob信息")
        Controller.get_controller_share_info(self)
        Controller.get_volume_info(self, "job")
        Controller.get_cron_job_schedule(self)
        self.logger.info("获取cronJob信息完成")
        return self.controller_info

    def create_cron_job_yaml(self, cron_job_info):
        self.logger.info("开始创建cronJob.yaml")
        self.logger.info("cronJob配置如下：")
        self.logger.info(cron_job_info)
        cron_job_yaml_j2 = '%s/templates/k8s/cronJob.yaml.j2' % sys.path[0]
        cron_job_yaml = '%s/cronJob.yaml' % self.k8s_path

        j2_to_file("server", cron_job_info, cron_job_yaml_j2, cron_job_yaml)
        self.logger.info("cronJob.yaml已生成。")
        apply_command_list = ["kubectl apply -f %s" % cron_job_yaml]
        return apply_command_list

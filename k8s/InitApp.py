#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import json
import time
import traceback
from docker.DockerImage import DockerImage
from k8s.K8sOpera import K8sOpera
from publicClass.Logger import Logger
from publicClass.JsonCheck import exchange_json
from publicClass.PublicFunc import set_ns_svc, get_files, shell_cmd, send_state_back


class InitApp:
    def __init__(self, settings_conf, app_info):
        self.logger = Logger("server")
        self.app_info = app_info
        self.settings_conf = settings_conf
        try:
            self.task_back_url = self.settings_conf['taskInfoBack']['url']
            self.task_flow_id = self.app_info['taskFlowId']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
        self.para_config = None

    def check(self):
        self.logger.info("接收服务操作json数据:'%r'" % self.app_info)
        try:
            tmp_post_json_data = json.loads(self.app_info['para'])
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1
        self.logger.info("转换前json数据:'%r'" % tmp_post_json_data)
        self.para_config = exchange_json(tmp_post_json_data)
        if isinstance(self.para_config, int) and self.para_config == 1:
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "(init)：发布json预处理失败")
            self.logger.error("发布json预处理失败")
            self.logger.error("错误退出程序")
            return 1
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "(init)：发布json预处理成功")
        self.logger.info("转换后json数据:'%r'" % self.para_config)
        return 0

    def deploy(self):
        try:
            global_config = self.para_config['global']
            mode = global_config['mode']
            docker_config = self.para_config['docker']
            docker_type = docker_config["useType"]
            k8s_config = self.para_config['kubernetes']
            k8s_announce_type = k8s_config['announceType']
            sys_name = global_config['sysName']
            app_name = global_config['appName']
            harbor_info = self.settings_conf['harborInfo']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1

        if mode == "new":
            mode_info = "全新发布"
        elif mode == "update":
            mode_info = "更新发布"
        else:
            mode_info = "其他"

        self.logger.info("本次发布模式：【%s】" % mode_info)
        self.logger.info("本次发布类别：run app")
        # date = time.strftime('%Y%m%d', time.localtime(time.time()))
        service_name, namespace = set_ns_svc(sys_name, app_name)
        image_info = {
            'dockerInfo': docker_config,
            'sysName': sys_name,
            'serviceName': service_name,
            'harborInfo': harbor_info
        }

        total_task_steps = 1
        current_task_step = 0

        if docker_type == "new":
            total_task_steps += 5
        else:
            total_task_steps += 1

        if k8s_announce_type != "none":
            total_task_steps += 1

        """获取镜像标签"""
        self.logger.info("创建应用镜像全名")
        current_task_step += 1

        str_image_final = DockerImage.create_full_image_name(image_info)
        # tag_final = "v20201214.0"
        if isinstance(str_image_final, int) and str_image_final == 1:
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "(%s/%s)：应用镜像名创建失败" % (str(current_task_step), str(total_task_steps)))
            self.logger.error("生成镜像全名失败")
            self.logger.error("错误退出程序")
            return 1
        self.logger.info("本次发布应用镜像全名为：%s" % str_image_final)
        send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                        "(%s/%s)：应用镜像名创建成功[%s]" % (str(current_task_step), str(total_task_steps), str_image_final))

        global_config.update({
            # 'tag': str_image_final
            'imageFullName': str_image_final
        })

        """docker部署部分"""
        if docker_type == "new":
            self.logger.info("全新制作镜像部分:")
            volume_mount_dir = []
            if k8s_announce_type != "none":
                try:
                    volume_info = k8s_config['container']['volume']
                    if volume_info.__contains__('emptyDir') and volume_info['emptyDir'] is not None:
                        for mount in volume_info['emptyDir']:
                            volume_mount_dir.append(mount['mountPath'])
                    if volume_info.__contains__('hostPath') and volume_info['hostPath'] is not None:
                        for mount in volume_info['hostPath']:
                            volume_mount_dir.append(mount['mountPath'])
                    if volume_info.__contains__('nfs') and volume_info['nfs'] is not None:
                        for mount in volume_info['nfs']:
                            volume_mount_dir.append(mount['mountPath'])
                    if volume_info.__contains__('pvc') and volume_info['pvc'] is not None:
                        for mount in volume_info['pvc']:
                            volume_mount_dir.append(mount['mountPath'])
                    if volume_info.__contains__('configMap') and volume_info['configMap'] is not None:
                        for mount in volume_info['configMap']:
                            volume_mount_dir.append(mount['mountPath'])
                except(KeyError, NameError):
                    self.logger.error(traceback.format_exc())
                    return 1
            try:
                docker_config['newImage'].update({
                    'volumeMountDir': volume_mount_dir
                })
            except(KeyError, NameError):
                self.logger.error(traceback.format_exc())
                return 1
            dockerfile = DockerImage(self.settings_conf, global_config, docker_config)
            self.logger.info("创建Dockerfile:")
            current_task_step += 1

            if dockerfile.create_dockerfile() == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：创建Dockerfile失败" % (str(current_task_step), str(total_task_steps)))
                print("Dockerfile创建失败")
                return 1
            # 2:正在跑，3：成功结束，5：失败结束
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：创建Dockerfile成功" % (str(current_task_step), str(total_task_steps)))
            print("Dockerfile创建成功")

            """从对象存储下载介质的方法"""
            self.logger.info("下载制作镜像所需介质:")
            current_task_step += 1

            if dockerfile.get_upload_files() == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：下载软件介质失败" % (str(current_task_step), str(total_task_steps)))
                print("软件介质获取失败")
                return 1

            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：下载介质成功" % (str(current_task_step), str(total_task_steps)))
            print("软件介质获取成功")
            self.logger.info("介质完成:")

            """制作镜像"""
            current_task_step += 1
            if dockerfile.build_image() == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：制作镜像失败" % (str(current_task_step), str(total_task_steps)))
                print("制作镜像失败")
                return 1

            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：制作镜像成功" % (str(current_task_step), str(total_task_steps)))
            print("制作镜像成功")

            """推送仓库"""
            current_task_step += 1
            if dockerfile.push_image() == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：镜像推送失败" % (str(current_task_step), str(total_task_steps)))
                print("镜像推送失败")
                return 1

            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：镜像推送成功" % (str(current_task_step), str(total_task_steps)))
            print("镜像推送成功")

        """k8s部署部分"""

        if k8s_announce_type != "none":
            self.logger.info("k8s部分:")
            k8s_opera = K8sOpera(self.settings_conf, global_config, k8s_config)
            current_task_step += 1
            if k8s_opera.create_resource_yaml() == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(%s/%s)：k8s资源清单创建出错" % (str(current_task_step), str(total_task_steps)))
                return 1
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "(%s/%s)：k8s资源清单创建成功" % (str(current_task_step), str(total_task_steps)))
            print("k8s资源清单创建成功")

        else:
            print("无k8s资源部署")

        time.sleep(10)
        send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                        "(%s/%s)：应用发布成功" % (str(total_task_steps), str(total_task_steps)))
        self.logger.info("本次发布完成...")
        return 0

    def opera(self):
        try:
            global_config = self.para_config['global']
            opera_type = self.app_info['operaType']
            sys_name = global_config['sysName']
            app_name = global_config['appName']
            k8s_base_path = self.settings_conf['pathInfo']['deployBasePath']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            return 1
        service_name, namespace = set_ns_svc(sys_name, app_name)

        k8s_path = "%s/%s/%s/YamlFile" % (k8s_base_path, sys_name, service_name)
        k8s_path = k8s_path.replace("//", "/")

        if not os.path.exists(k8s_path):
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "(1/1)：服务停止出错,目录[%s]不存在" % k8s_path)
            return 1
        if opera_type == "6":
            k8s_current_yaml_file = get_files(k8s_path, '.yaml')
            code = 0
            if not k8s_current_yaml_file:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：服务停止出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                return 1

            matchers = ['deployment', 'statefulset', 'job', 'cronjob']
            matching = [s for s in k8s_current_yaml_file if any(xs in s for xs in matchers)]
            for yaml_file in matching:
                cmd_line = "kubectl delete -f %s" % yaml_file
                code = code or shell_cmd("server", cmd_line)
            if code == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：服务停止出错")
            else:
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "(1/1)：服务停止成功")
            return code
        elif opera_type == "5":
            self.logger.info("启动服务")
            if not os.path.exists("%s/appStart.sh" % k8s_path):
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：服务启动出错,启动脚本[%s/appStart.sh]不存在" % k8s_path)
                return 1
            cmd_line = "sh %s/appStart.sh" % k8s_path
            code = shell_cmd("server", cmd_line)
            if code == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：服务启动出错")
                return code
            else:
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "(1/1)：服务启动成功")

            if os.path.exists("%s/deleteNoNeedYaml.sh" % k8s_path):
                cmd_line = "sh %s/deleteNoNeedYaml.sh" % k8s_path
                shell_cmd("server", cmd_line)
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "(extra)：存在记录较上次发布多余资源，并删除")
            return code
        elif opera_type == "4":
            k8s_current_yaml_file = get_files(k8s_path, '.yaml')
            code = 0
            if not k8s_current_yaml_file:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：应用环境回收出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                return 1
            for yaml_file in k8s_current_yaml_file:
                cmd_line = "kubectl delete -f %s" % yaml_file
                code = code or shell_cmd("server", cmd_line)
            if code == 1:
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "(1/1)：应用环境回收出错")
            else:
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "(1/1)：应用环境回收成功")
            return code
        else:
            return 0

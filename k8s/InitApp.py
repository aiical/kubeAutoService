#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import os
import time
import traceback
from flask import abort
from docker.DockerImage import DockerImage
from k8s.InitProject import InitProject
from k8s.K8sOpera import K8sOpera
from publicClass.PublicFunc import set_ns_svc, get_files, shell_cmd, send_state_back


class InitApp(InitProject):
    def __init__(self, settings_conf, info):
        InitProject.__init__(self, settings_conf, info)

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
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
        else:
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
                'taskBackUrl': self.task_back_url,
                'taskFlowId': self.task_flow_id,
                'dockerInfo': docker_config,
                'sysName': sys_name,
                'serviceName': service_name,
                'harborInfo': harbor_info
            }

            """获取镜像标签"""
            self.logger.info("创建应用镜像全名")

            str_image_final = DockerImage.create_full_image_name(image_info)

            self.logger.info("本次发布应用镜像全名为：%s" % str_image_final)
            send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                            "[INFO]：应用镜像名创建成功[%s]" % str_image_final)

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
                        send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                        "[ERROR]：%s" % traceback.format_exc())
                        abort(404)
                        # return 1
                try:
                    docker_config['newImage'].update({
                        'volumeMountDir': volume_mount_dir
                    })
                except(KeyError, NameError):
                    self.logger.error(traceback.format_exc())
                    send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                    "[ERROR]：%s" % traceback.format_exc())
                    abort(404)
                    # return 1
                else:
                    dockerfile = DockerImage(self.settings_conf, global_config, docker_config)
                    self.logger.info("创建Dockerfile:")
                    # current_task_step += 1

                    dockerfile.create_dockerfile()
                    # 2:正在跑，3：成功结束，5：失败结束
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                    "[INFO]：创建Dockerfile成功")
                    # print("Dockerfile创建成功")

                    """从对象存储下载介质的方法"""
                    self.logger.info("下载制作镜像所需介质:")
                    # current_task_step += 1

                    dockerfile.get_upload_files()
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                    "[INFO]：下载介质成功")
                    # print("软件介质获取成功")
                    self.logger.info("下载介质成功:")

                    """制作镜像"""
                    # current_task_step += 1
                    dockerfile.build_image()
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                    "[INFO]：制作镜像成功")
                    # print("制作镜像成功")

                    """推送仓库"""
                    # current_task_step += 1
                    dockerfile.push_image()
                    send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                    "[INFO]：镜像推送成功")
                    # print("镜像推送成功")

            """k8s部署部分"""

            if k8s_announce_type != "none":
                self.logger.info("k8s部分:")
                k8s_opera = K8sOpera(self.settings_conf, global_config, k8s_config)
                # current_task_step += 1
                k8s_opera.create_resource_yaml()
                send_state_back(self.task_back_url, self.task_flow_id, 2, 3,
                                "[INFO]：k8s资源清单创建成功")
                # print("k8s资源清单创建成功")
            else:
                self.logger.warn("无k8s资源部署")
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "[FINISH WHIT WARN]：无k8s资源部署")
            time.sleep(2)
            send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                            "[FINISH]：应用发布成功")
            self.logger.info("本次发布完成...")

    def opera(self):
        try:
            global_config = self.para_config['global']
            opera_type = self.info['operaType']
            sys_name = global_config['sysName']
            app_name = global_config['appName']
            k8s_base_path = self.settings_conf['pathInfo']['deployBasePath']
        except(KeyError, NameError):
            self.logger.error(traceback.format_exc())
            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                            "[ERROR]：%s" % traceback.format_exc())
            abort(404)
            # return 1
        else:
            service_name, namespace = set_ns_svc(sys_name, app_name)

            k8s_path = "%s/%s/%s/YamlFile" % (k8s_base_path, sys_name, service_name)
            k8s_path = k8s_path.replace("//", "/")

            if not os.path.exists(k8s_path):
                self.logger.error("服务停止出错,目录[%s]不存在" % k8s_path)
                send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                "[ERROR]：服务停止出错,目录[%s]不存在" % k8s_path)
                abort(404)
                # return 1
            if opera_type == "6":
                self.logger.info("停止服务")
                k8s_current_yaml_file = get_files(k8s_path, '.yaml')
                # code = 0
                if not k8s_current_yaml_file:
                    self.logger.error("服务停止出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                    send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                    "[ERROR]：服务停止出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                    abort(404)
                    # return 1

                matchers = ['deployment', 'statefulset', 'job', 'cronjob']
                matching = [s for s in k8s_current_yaml_file if any(xs in s for xs in matchers)]
                for yaml_file in matching:
                    cmd_line = "kubectl delete -f %s" % yaml_file
                    if not shell_cmd("server", cmd_line):
                        send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                        "[ERROR]:COMMAND:%s执行出错" % cmd_line)
                        abort(404)

                self.logger.info("服务停止成功")
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "[FINISH]：服务停止成功")
                # return code
            elif opera_type == "5":
                self.logger.info("启动服务")
                if not os.path.exists("%s/appStart.sh" % k8s_path):
                    self.logger.error("服务启动出错,启动脚本[%s/appStart.sh]不存在" % k8s_path)
                    send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                    "[ERROR]：服务启动出错,启动脚本[%s/appStart.sh]不存在" % k8s_path)
                    abort(404)
                    # return 1
                cmd_line = "sh %s/appStart.sh" % k8s_path
                # code = shell_cmd("server", cmd_line)
                if not shell_cmd("server", cmd_line):
                    self.logger.error("服务启动出错")
                    send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                    "[ERROR]：服务启动出错")
                    abort(404)
                    # return code
                else:
                    if os.path.exists("%s/deleteNoNeedYaml.sh" % k8s_path):
                        cmd_line = "sh %s/deleteNoNeedYaml.sh" % k8s_path
                        if not shell_cmd("server", cmd_line):
                            self.logger.error("删除较上次发布多余资源失败")
                            send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                            "[ERROR]：删除较上次发布多余资源失败")
                            abort(404)
                        else:
                            self.logger.info("删除较上次发布多余资源成功")
                            send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                            "[INFO]：删除较上次发布多余资源成功")
                    self.logger.info("服务启动成功")
                    send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                    "[FINISH]：服务启动成功")

            elif opera_type == "4":
                k8s_current_yaml_file = get_files(k8s_path, '.yaml')

                if not k8s_current_yaml_file:
                    self.logger.error("应用环境回收出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                    send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                    "[ERROR]：应用环境回收出错,目录[%s]下不存在k8s资源清单" % k8s_path)
                    abort(404)
                for yaml_file in k8s_current_yaml_file:
                    cmd_line = "kubectl delete -f %s" % yaml_file
                    if not shell_cmd("server", cmd_line):
                        send_state_back(self.task_back_url, self.task_flow_id, 5, 5,
                                        "[ERROR]:COMMAND:%s执行出错" % cmd_line)
                        abort(404)

                self.logger.info("应用环境回收成功")
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "[FINISH]：应用环境回收成功")
                # return code
            else:
                self.logger.warn("无效操作码")
                send_state_back(self.task_back_url, self.task_flow_id, 3, 3,
                                "[FINISH WHIT WARN]：无效操作码")

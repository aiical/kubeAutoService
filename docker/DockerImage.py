#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import time
import os
import sys
import re
import asyncio
import traceback
from publicClass.Logger import Logger
from publicClass.PublicFunc import shell_cmd, is_compress, j2_to_file, set_ns_svc, get_remote_file
from publicClass.HttpFunc import harbor_api_http_get, harbor_api_http_post


class DockerImage:
    def __init__(self, settings_conf, global_info, docker_info):
        logger = Logger("server")
        self.global_info = global_info
        self.docker_info = docker_info['newImage']
        """读取settings设置"""
        conf = settings_conf

        self.tomcat_conf = sys.path[0] + '/conf/tomcat_version.yaml'
        self.jdk_conf = sys.path[0] + '/conf/jdk_version.yaml'

        """生产Dockerfile、介质存放地址"""
        self.sys_name = self.global_info['sysName']
        self.app_name = self.global_info['appName']

        """获取服务名和名称空间"""
        self.service_name, namespace = set_ns_svc(self.sys_name, self.app_name)

        deploy_base_path = conf['pathInfo']['deployBasePath']

        self.docker_path = "%s/%s/%s/DockerImage" % (deploy_base_path, self.sys_name, self.service_name)
        self.docker_path = self.docker_path.replace("//", "/")

        """仓库信息"""
        self.harbor_ip = conf['harborInfo']['host']
        self.harbor_user = conf['harborInfo']['user']
        self.harbor_password = conf['harborInfo']['password']
        # self.app_repository = "%s/app" % self.harbor_ip
        # self.library_repository = "%s/library" % self.harbor_ip

        """备份全有dockerfile目录
        DockerImage_yyyymmddHh24miss
        """

        dir_bak_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        docker_bak_path = self.docker_path + '_' + dir_bak_time
        if os.path.exists(self.docker_path):
            str_cmd = "mv %s %s" % (self.docker_path, docker_bak_path)
            logger.info("备份目录%s到%s" % (self.docker_path, docker_bak_path))
            logger.info("COMMAND: %s" % str_cmd)
            shell_cmd("server", str_cmd)

        os.makedirs(self.docker_path)

        """工具介质路径"""
        self.tool_path = conf['pathInfo']['toolPath']

        self.object_storage_conf = conf['objectStorage']

    """docker镜像属性
    docker镜像所需属性，用于build，tag，push动作
    属性：image，tag
    """

    @staticmethod
    def create_full_image_name(image_info):
        logger = Logger("server")
        docker_info = image_info['dockerInfo']
        docker_type = docker_info['useType']
        sys_name = image_info['sysName']
        service_name = image_info['serviceName']
        harbor_ip = image_info['harborInfo']['host']
        harbor_user = image_info['harborInfo']['user']
        harbor_password = image_info['harborInfo']['password']
        if docker_type == 'new':
            logger.info("本次发布需要制作镜像")
            project_name = sys_name
            date = time.strftime('%Y%m%d', time.localtime(time.time()))
            DockerImage.create_harbor_project(project_name, harbor_ip, harbor_user, harbor_password)

            harbor_url = "https://%s/api/v2.0/projects/%s/repositories/%s/artifacts" \
                         "?with_tag=true&with_label=false" \
                         "&with_scan_overview=false&with_signature=false&with_immutable_status=false" \
                         % (harbor_ip, project_name, service_name)
            logger.info("镜像查询harbor_url：[%s]" % harbor_url)
            resp_status, artifacts_list = asyncio.run(harbor_api_http_get(harbor_url, harbor_user, harbor_password))

            if isinstance(artifacts_list, int) and artifacts_list == 1:
                logger.error("获取镜像artifacts_list报错")
                return 1
            logger.info("获取镜像artifacts_list成功")
            all_tag_list = []
            for artifacts in artifacts_list:
                artifact_tags = artifacts['tags']
                for tag in artifact_tags:
                    all_tag_list.append(tag['name'])

            tag_today_list = []
            for item in all_tag_list:
                if item[1:9] == date:
                    tag_today_list.append(item)

            if not tag_today_list:
                final_tag = "v" + date + ".0"
            else:
                num_list = []
                for item in tag_today_list:
                    num = int(item.split(".")[-1])
                    num_list.append(num)
                num_list.sort()
                max_num = num_list[-1]
                add_num = max_num + 1
                final_tag = "v" + date + "." + str(add_num)
            logger.info("创建新镜像标签final_tag：[%s]" % final_tag)
            str_image_final = "%s/%s/%s:%s" % (harbor_ip, project_name, service_name, final_tag)

        else:
            logger.info("本次发布不进行制作镜像")
            exist_image_info = docker_info['existImage']
            project_name = exist_image_info['projectName']
            image_name = exist_image_info['imageName']
            image_tag = exist_image_info['imageTag']
            logger.info("判断填写镜像是否存在")
            if project_name and image_name and image_tag:
                if DockerImage.is_harbor_tag_exist(
                        project_name, image_name, image_tag, harbor_ip, harbor_user, harbor_password):
                    str_image_final = "%s/%s/%s:%s" % (harbor_ip, project_name, image_name, image_tag)
                else:
                    return 1
            else:
                logger.error("镜像不存在")
                return 1
        logger.info(str_image_final)
        return str_image_final

    @staticmethod
    def create_harbor_project(project_name, harbor_ip, harbor_user, harbor_password):
        logger = Logger("server")
        harbor_url = "https://%s/api/v2.0/projects?name=%s" % (harbor_ip, project_name)
        resp_status, project_list = asyncio.run(harbor_api_http_get(harbor_url, harbor_user, harbor_password))
        if len(project_list) == 0:
            logger.info("harbor[%s]中不存在仓库[%s]，准备新建。。。" % (harbor_ip, project_name))
            post_url = "https://%s/api/v2.0/projects" % harbor_ip
            past_data = '{"project_name": "%s", "public": true}' % project_name
            post_code = asyncio.run(harbor_api_http_post(post_url, past_data, harbor_user, harbor_password))
            if post_code == 201:
                logger.info("harbor[%s]中新建仓库[%s]成功" % (harbor_ip, project_name))
            else:
                logger.error("harbor[%s]中新建仓库[%s]失败，失败码为%s" % (harbor_ip, project_name, str(post_code)))
        else:
            logger.info("harbor[%s]中存在仓库[%s]，继续。。。" % (harbor_ip, project_name))

    @staticmethod
    def is_harbor_tag_exist(project, repository, tag, harbor_ip, harbor_user, harbor_password):
        logger = Logger("server")
        str_image_final = "%s/%s/%s:%s" % (harbor_ip, project, repository, tag)
        harbor_url = "https://%s/api/v2.0/projects/%s/repositories/%s/artifacts/%s/tags?q=name%%3D%s" % (
            harbor_ip, project, repository, tag, tag)
        resp_status, tag_list = asyncio.run(harbor_api_http_get(harbor_url, harbor_user, harbor_password))
        if tag_list.__contains__("errors"):
            logger.error("镜像%s不存在" % str_image_final)
            return False
        else:
            if len(tag_list) == 0:
                logger.error("镜像%s不存在" % str_image_final)
                return False
            else:
                logger.info("镜像%s存在" % str_image_final)
                return True

    """dockerfile属性
    dockerfile生成属性
    属性：FROM, MAINTAINER, ADD, COPY, WORKDIR, ENV, RUN, EXPOSE, ENTRYPOINT
         CMD, LABELS, VOLUME, USER, ARG, ONBUILD
    """

    def __get_from(self):
        tmp_from = self.docker_info['from']
        project_name = tmp_from['projectName']
        image_name = tmp_from['imageName']
        image_tag = tmp_from['imageTag']
        base_from = "%s/%s/%s:%s" % (self.harbor_ip, project_name, image_name, image_tag)
        base_from = base_from.replace("//", "/")
        return base_from

    def __get_maintainer(self):
        maintainer = self.docker_info['maintainer']
        return maintainer

    def __get_file(self):
        tmp_files = self.docker_info['file']
        file_add = []
        file_copy = []
        if tmp_files:
            for file in tmp_files:
                file_name = file['name']
                file_dest = file['dest']
                if is_compress(file_name):
                    file_add.append(
                        "%s %s" % (file_name, file_dest)
                    )
                else:
                    file_copy.append(
                        "%s %s" % (file_name, file_dest)
                    )
        return file_add, file_copy

    def __get_run(self):
        list_run = []
        dft_run = "RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' > /etc/timezone"
        list_run.append(dft_run)
        tmp_run = self.docker_info['run']
        if tmp_run:
            for item in tmp_run:
                list_run.append("RUN %s" % item)
        return list_run

    def __get_expose(self):
        expose = ""
        tmp_expose = str(self.docker_info['expose'])
        if tmp_expose:
            expose = tmp_expose
        return expose

    def __get_entry_point(self):
        entry_point = ""
        tmp_entry_point = self.docker_info['entrypoint']
        if tmp_entry_point:
            for item in tmp_entry_point:
                if self.global_info["skyWalking"]["flag"] == "Y":
                    item_res = re.sub("java ", "java ${AGENT_OPTS} ", item)
                    entry_point += item_res + " &&"
                else:
                    entry_point += item + " &&"
            entry_point = entry_point[:-3]
        return entry_point

    def __get_cmd(self):
        pass

    def __get_label(self):
        pass

    def __get_work_dir(self):
        work_dir = self.docker_info['workdir']
        return work_dir

    def __get_volume(self):
        pass

    def __get_user(self):
        user_info = {}
        if self.docker_info.__contains__('user'):
            if self.docker_info['user']:
                user_name = self.docker_info['user']
                user_info.update({
                    'user': user_name,
                    'run': [
                        'mkdir -p /%s' % user_name,
                        'groupadd -g 1000 %s && useradd -g %s -d /%s -m %s' % (
                            user_name, user_name, user_name, user_name),
                        'chown -R %s:%s /%s' % (
                            user_name, user_name, user_name)
                    ]
                })
        return user_info

    def __get_arg(self):
        pass

    def __get_on_build(self):
        pass

    def __get_env(self):
        env_list = []
        logger = Logger("server")
        try:
            tmp_env = self.docker_info['env']
            if tmp_env:
                for item in tmp_env:
                    name = item['name']
                    value = item['value']
                    env_list.append("%s %s" % (name, str(value)))
            return env_list
        except Exception:
            logger.error(traceback.format_exc())

    """dockerfile中的tomcat和jdk
    若镜像中包含tomcat和jdk，根据版本获取dockerfile所需信息
    """

    def __get_tomcat(self):
        tmp_tomcat = self.docker_info['tomcat']
        tomcat_flag = tmp_tomcat['flag']
        tomcat_dict = {}
        if tomcat_flag == "Y":
            tomcat_name = tmp_tomcat['name']
            tomcat_dir = tomcat_name.replace(".tar.gz", "")
            tomcat_dest = tmp_tomcat['dest']
            tomcat_file = tmp_tomcat['file']
            tomcat_copy = []
            tomcat_add = []
            add_tom_info = "%s %s" % (tomcat_name, tomcat_dest)
            tomcat_add.append(add_tom_info)
            if tomcat_file:
                for file in tomcat_file:
                    file_name = file['name']
                    file_dest = file['dest']
                    if is_compress(file_name):
                        add_info = "%s %s/%s/%s" % (file_name, tomcat_dest, tomcat_dir, file_dest)
                        add_info.replace("//", "/")
                        tomcat_add.append(add_info)
                    else:
                        copy_info = "%s %s/%s/%s" % (file_name, tomcat_dest, tomcat_dir, file_dest)
                        copy_info.replace("//", "/")
                        tomcat_copy.append(copy_info)

            tmp_tomcat_run = "RUN chmod 777 %s/%s/bin/*.sh" % (tomcat_dest, tomcat_dir)
            tomcat_run = tmp_tomcat_run.replace("//", "/")
            tomcat_endpoint = "%s/%s/bin/catalina.sh run" % (tomcat_dest, tomcat_dir)
            tomcat_endpoint = tomcat_endpoint.replace("//", "/")
            tomcat_dict.update({
                'tomcat_add': tomcat_add,
                'tomcat_copy': tomcat_copy,
                'tomcat_run': tomcat_run,
                'tomcat_endpoint': tomcat_endpoint
            })
        return tomcat_dict

    def __get_jdk(self):
        tmp_jdk = self.docker_info['jdk']
        jdk_flag = tmp_jdk['flag']
        jdk_dict = {}
        if jdk_flag == "Y":
            jdk_name = tmp_jdk['name']
            jdk_dir = jdk_name.replace(".tar.gz", "")

            jdk_dest = tmp_jdk['dest']
            jdk_file = tmp_jdk['file']
            jdk_copy = []
            jdk_add = []
            add_tom_info = "%s %s" % (jdk_name, jdk_dest)
            jdk_add.append(add_tom_info)
            if jdk_file:
                for file in jdk_file:
                    file_name = file['name']
                    file_dest = file['dest']
                    if is_compress(file_name):
                        add_info = "%s %s/%s/%s" % (file_name, jdk_dest, jdk_dir, file_dest)
                        add_info.replace("//", "/")
                        jdk_add.append(add_info)
                    else:
                        copy_info = "%s %s/%s/%s" % (file_name, jdk_dest, jdk_dir, file_dest)
                        copy_info.replace("//", "/")
                        jdk_copy.append(copy_info)

            tmp_java_home = jdk_dest + "/" + jdk_dir
            java_home = tmp_java_home.replace("//", "/")
            jdk_env = [
                "JAVA_HOME %s" % java_home,
                "PATH $PATH:$JAVA_HOME/bin"
            ]

            jdk_dict.update({
                'jdk_add': jdk_add,
                'jdk_copy': jdk_copy,
                'jdk_env': jdk_env
            })
        return jdk_dict

    """镜像中要提前创建的目录
    若有需要提前创建的目录时，写入RUN信息
    """

    def __get_mkdir(self):
        list_dir = []
        tmp_dir_mk = self.docker_info['mkdir']
        tmp_file = self.docker_info['file']
        volume_mount_dir = self.docker_info['volumeMountDir']

        if tmp_dir_mk is None:
            tmp_dir_mk = []
        tmp_dir_mk.extend(volume_mount_dir)

        for item in tmp_file:
            tmp_dir_mk.append(item['dest'])
        tmp_dir = list(set(tmp_dir_mk))
        if '/home' in tmp_dir:
            tmp_dir.remove('/home')
        if '/home/' in tmp_dir:
            tmp_dir.remove('/home/')
        if '' in tmp_dir:
            tmp_dir.remove('')
        if tmp_dir:
            for item in tmp_dir:
                list_dir.append("RUN mkdir -p %s" % item)
        return list_dir

    def get_upload_files(self):
        logger = Logger("server")
        file_list = []
        logger.info("从对象存储获取制作镜像所需介质")
        if self.global_info["skyWalking"]["flag"] == "Y":
            sky_walking_media = {
                'name': self.global_info['skyWalking']['name'],
                'dest': self.global_info['skyWalking']['dest'],
                'key': self.global_info['skyWalking']['key'],
                'md5Code': self.global_info['skyWalking']['md5Code']
            }
            file_list.append(sky_walking_media)
        if self.docker_info['tomcat']['flag'] == 'Y':
            tomcat_media = {
                'name': self.docker_info['tomcat']['name'],
                'dest': self.docker_info['tomcat']['dest'],
                'key': self.docker_info['tomcat']['key'],
                'md5Code': self.docker_info['tomcat']['md5Code']
            }
            file_list.append(tomcat_media)
            tomcat_file = self.docker_info['tomcat']['file']
            if tomcat_file:
                for file in tomcat_file:
                    file_list.append(file)
        if self.docker_info['jdk']['flag'] == 'Y':
            jdk_media = {
                'name': self.docker_info['jdk']['name'],
                'dest': self.docker_info['jdk']['dest'],
                'key': self.docker_info['jdk']['key'],
                'md5Code': self.docker_info['jdk']['md5Code']
            }
            file_list.append(jdk_media)
            jdk_file = self.docker_info['jdk']['file']
            if jdk_file:
                for file in jdk_file:
                    file_list.append(file)
        other_files = self.docker_info['file']
        if other_files:
            for file in other_files:
                file_list.append(file)
        for file in file_list:
            name = file['name']
            key = file['key']
            md5_code = file['md5Code']
            # post_fields = "fileid=%s&accessKey=%s&clientIp=%s" % (key, access_key, client_ip)
            dest_file_full_name = "%s/%s" % (self.docker_path, name)
            if get_remote_file("server", self.object_storage_conf, key, md5_code, dest_file_full_name) == 1:
                logger.error("介质%s远程下载失败！" % name)
                return 1
            logger.info("介质%s远程下载成功！" % name)
        return 0

    """创建dockerfile函数
    """
    def create_dockerfile(self):
        """创建dockerfile函数
        FROM, MAINTAINER, ADD, COPY, WORKDIR, ENV, RUN, EXPOSE, ENTRYPOINT等信息写入Dockerfile
        :return: 无
        """
        logger = Logger("server")
        logger.info("开始配置Dockerfile")
        """FROM"""
        str_from = self.__get_from()
        """MAINTAINER"""
        str_maintainer = self.__get_maintainer()
        """WORKDIR"""
        str_work_dir = self.__get_work_dir()
        """RUN下面的mkdir"""
        list_mkdir = self.__get_mkdir()

        """jdk"""
        if isinstance(self.__get_jdk(), int):
            return 1

        jdk_dict = self.__get_jdk()
        if jdk_dict:
            jdk_add = jdk_dict['jdk_add']
            jdk_copy = jdk_dict['jdk_copy']
            jdk_env = jdk_dict['jdk_env']
        else:
            jdk_add = []
            jdk_copy = []
            jdk_env = []
        """tomcat"""
        if isinstance(self.__get_tomcat(), int):
            return 1

        tomcat_dict = self.__get_tomcat()
        if tomcat_dict:
            tomcat_add = tomcat_dict['tomcat_add']
            tomcat_copy = tomcat_dict['tomcat_copy']
            tomcat_run = tomcat_dict['tomcat_run']
            tomcat_endpoint = tomcat_dict['tomcat_endpoint']
        else:
            tomcat_add = []
            tomcat_copy = []
            tomcat_run = ""
            tomcat_endpoint = ""

        """ENV"""
        env_list = []
        if jdk_env:
            env_list.extend(jdk_env)

        other_env = self.__get_env()
        if other_env:
            env_list.extend(other_env)

        """ADD和COPY的文件"""
        file_add, file_copy = self.__get_file()

        """ADD"""
        add_list = []
        if tomcat_add:
            add_list.extend(tomcat_add)
        if jdk_add:
            add_list.extend(jdk_add)
        if self.global_info["skyWalking"]["flag"] == "Y":
            add_list.append("%s /home" % self.global_info["skyWalking"]["name"])
        if file_add:
            add_list.extend(file_add)

        """COPY"""
        copy_list = []
        if tomcat_copy:
            copy_list.extend(tomcat_copy)
        if jdk_copy:
            copy_list.extend(jdk_copy)
        if file_copy:
            copy_list.extend(file_copy)

        """RUN其他命令"""
        list_run = []
        default_run_list = self.__get_run()
        if default_run_list:
            list_run.extend(default_run_list)
        if tomcat_run:
            list_run.append(tomcat_run)

        """EXPOSE"""
        str_expose = self.__get_expose()

        """ENTRYPOINT"""
        other_entry_point = self.__get_entry_point()
        # str_entry_point = ""
        # if other_entry_point:
        #     str_entry_point += other_entry_point + " && "
        # if tomcat_endpoint:
        #     str_entry_point += tomcat_endpoint + " && "
        # if str_entry_point:
        #     str_entry_point = str_entry_point[:-4]
        if tomcat_endpoint:
            str_entry_point = tomcat_endpoint
        else:
            str_entry_point = other_entry_point
        if str_entry_point == "":
            logger.error("未填写ENTRYPOINT")
            return 1

        docker_file_conf = {
            'baseFrom': str_from,
            'maintainer': str_maintainer,
            'workdir': str_work_dir,
            'envList': env_list,
            'mkdirList': list_mkdir,
            'addList': add_list,
            'copyList': copy_list,
            'runList': list_run,
            'expose': str_expose,
            'entrypoint': str_entry_point
        }

        docker_file_j2 = '%s/templates/docker/Dockerfile.j2' % sys.path[0]
        docker_file = '%s/Dockerfile' % self.docker_path
        if j2_to_file("server", docker_file_conf, docker_file_j2, docker_file) == 1:
            logger.error("Dockerfile生成失败。")
            return 1
        logger.info("Dockerfile已生成。")
        return 0

    def build_image(self):
        """docker制作镜像函数
        docker制作镜像，打标签，推送仓库
        :return:
        """
        logger = Logger("server")
        logger.info("docker镜像制作:")

        dockerfile_path = "%s/Dockerfile" % self.docker_path
        dockerfile_path = dockerfile_path.replace("//", "/")
        if not (os.path.exists(dockerfile_path)
                and os.path.isfile(dockerfile_path)):
            logger.error("%s下Dockerfile不存在" % self.docker_path)
            logger.error("错误退出程序")
            return 1
        else:
            os.chdir(self.docker_path)

            image_full_name = self.global_info['imageFullName']

            """参数检查"""
            logger.info("参数检查:")

            logger.info("仓库镜像:标签 image_full_name = %s" % image_full_name)
            logger.info("Dockerfile路径 docker_path = %s" % self.docker_path)

            """docker build"""
            logger.info("开始制作镜像build...")
            # str_cmd = "docker build -t " + image_tag + " ."
            str_cmd = "docker build -t " + image_full_name + " ."
            logger.info("COMMAND: %s" % str_cmd)
            logger.info("------------------------------------------------------------------")
            if shell_cmd("server", str_cmd) == 1:
                return 1
            logger.info("镜像制作完成。")
            logger.info("------------------------------------------------------------------")

            # """docker push"""
            # logger.info("推送镜像仓库...")
            # str_cmd = "docker push %s" % image_full_name
            # logger.info("COMMAND: %s" % str_cmd)
            # logger.info("------------------------------------------------------------------")
            # if shell_cmd(str_cmd) == 1:
            #     return 1
            # logger.info("推送完成。")
            # logger.info("------------------------------------------------------------------")
            return 0

    def push_image(self):
        logger = Logger("server")
        logger.info("docker镜像推送:")
        image_full_name = self.global_info['imageFullName']
        str_cmd = "docker push %s" % image_full_name
        logger.info("COMMAND: %s" % str_cmd)
        logger.info("------------------------------------------------------------------")
        if shell_cmd("server", str_cmd) == 1:
            return 1
        logger.info("推送完成。")
        logger.info("------------------------------------------------------------------")
        return 0

#!/bin/bash

s_run_num=$(ps -ef |grep "kubeAutoService/app.py" |grep -v grep |wc -l)
if [ "${s_run_num}" == "0" ];then
  nohup python3.7 -u /opt/Project/kubeAutoService/app.py > /dev/null 2>&1 &
  echo "自动发布服务启动。"
  ps -ef |grep "kubeAutoService/app.py" |grep -v grep
else
  echo "自动发布服务已存在，无需重复启动。"
fi
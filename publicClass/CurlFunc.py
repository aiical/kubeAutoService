#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import json
import re
import pycurl
import traceback
# from datetime import datetime, timezone, timedelta
from io import BytesIO
from publicClass.Logger import Logger


def curl_harbor_get_func(url, user, password):
    logger = Logger("server")
    c = pycurl.Curl()
    head = ["Content-Type: application/json", "accept: application/json"]
    buffer = BytesIO()
    user_pwd = "%s:%s" % (user, password)
    try:
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.USERPWD, user_pwd)
        c.setopt(c.HTTPHEADER, head)
        c.setopt(c.CONNECTTIMEOUT, 60)
        c.setopt(c.TIMEOUT, 600)
        c.perform()
        c.close()
        result = buffer.getvalue()
        buffer.close()
        data_json = json.loads(result)
        return data_json
    except TypeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except IndentationError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except NameError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except pycurl.error as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except json.decoder.JSONDecodeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1


def curl_harbor_post_func(url, post_fields, user, password):
    logger = Logger("server")
    c = pycurl.Curl()
    head = ["Content-Type: application/json", "accept: application/json"]
    buffer = BytesIO()
    user_pwd = "%s:%s" % (user, password)
    try:
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.POST, 1)
        c.setopt(c.USERPWD, user_pwd)
        c.setopt(c.HTTPHEADER, head)
        c.setopt(c.CONNECTTIMEOUT, 60)
        c.setopt(c.TIMEOUT, 600)
        c.setopt(c.POSTFIELDS, post_fields)
        c.perform()
        response_code = c.getinfo(c.RESPONSE_CODE)
        c.close()
        buffer.close()
        return response_code
    except TypeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except IndentationError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except NameError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except pycurl.error as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except json.decoder.JSONDecodeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1


def curl_file_func(url, post_fields, file_dest):
    logger = Logger("server")
    c = pycurl.Curl()
    buffer = BytesIO()
    try:
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.POST, 1)
        c.setopt(c.POSTFIELDS, post_fields)
        c.setopt(c.CONNECTTIMEOUT, 60)
        c.setopt(c.TIMEOUT, 600)
        c.perform()
        c.close()
        result = buffer.getvalue()
        with open(file_dest, "wb") as f:
            f.write(result)
        buffer.close()
        return 0
    except TypeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except IndentationError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except NameError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except pycurl.error as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except json.decoder.JSONDecodeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1


"""
import pycurl
from io import BytesIO
import json
c = pycurl.Curl()
url = "https://10.3.137.11:8443/api/v1/namespaces/nwp-system/pods?labelSelector=app=nwp-web"
head = ["Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjR2T010cGJRRG8wZnNrWkpULWlTTWc1R2NlVmZkSWlVX0E4TnFOYnd4aGcifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6InNhLWF1dG8tdG9rZW4tejc0dm4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoic2EtYXV0byIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6Ijg3NmFkMzIyLWIyOWQtNGE3ZS1hNWNjLTllYTU5YzAzYjQwMyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OnNhLWF1dG8ifQ.ki8M0npYcie4YVl1q00AxeB5_ZuWnsjrEOnLdrsnaWZm-mItIVuWNXvL1z4yGs79NWm5sE6WUjmRuPZqeh7_Olu25K7qBAMEOe6lqQhYQtlRyGIfKI69WhTM2Pjjp5lWeFx6KiRVlvX4tYqX-3Vkf1DUf8sUy40cmp8PR2eh2JxEK5R3semc3VhtQ7F_FqtwFBty80Tiy_0OJgoZ1_hgo4xGZ_JWCPjoTBPcGZOiBqDtiLh0sJ1eqFbUWTgJ4NfuaSkHITAziQnzZGqTcXEggDx6wYf7781R7VhFcIyw-6jDDZTkTW5qtVfy3ZOdVCorEuIhdjVOttMmfrnc3Gi0qA"]
c.setopt(c.URL, url)
buffer = BytesIO()
c.setopt(c.WRITEDATA, buffer)
c.setopt(pycurl.HTTPHEADER, head)
c.perform()
result = buffer.getvalue()
data_json = json.loads(result)
print(data_json['items'][0]['status']['containerStatuses']) 
"""


def curl_k8s_api_json(url, token):
    logger = Logger("server")
    # tz = timezone(timedelta(hours=+8))
    c = pycurl.Curl()
    # c = pycurl.CurlMulti()
    head = ["Authorization: Bearer %s" % token]
    buffer = BytesIO()
    try:
        # logger.info("curl_k8s_api_json start: %s" % datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        logger.info("curl_k8s_api_json start:")
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, buffer.write)
        c.setopt(pycurl.HTTPHEADER, head)
        c.setopt(pycurl.CONNECTTIMEOUT, 15)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.setopt(pycurl.MAXREDIRS, 5)
        c.setopt(pycurl.NOSIGNAL, 1)
        c.setopt(pycurl.TIMEOUT, 15)
        c.perform()
        logger.info("CONNECT_TIME: %s" % c.getinfo(pycurl.CONNECT_TIME))
        logger.info("PRETRANSFER_TIME: %s" % c.getinfo(pycurl.PRETRANSFER_TIME))
        logger.info("TOTAL_TIME: %s" % c.getinfo(pycurl.TOTAL_TIME))
        logger.info("REDIRECT_TIME: %s" % c.getinfo(pycurl.REDIRECT_TIME))
        logger.info("REDIRECT_COUNT: %s" % c.getinfo(pycurl.REDIRECT_COUNT))

        c.close()
        result = buffer.getvalue()
        buffer.close()
        data_json = json.loads(result)
        logger.info("curl_k8s_api_json end:")
        # logger.info("curl_k8s_api_json end: %s" % datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        return data_json
    except TypeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except IndentationError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except NameError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except pycurl.error as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except json.decoder.JSONDecodeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1


def curl_k8s_api_text(url, token):
    logger = Logger("server")
    ansi_cleaner = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]")
    c = pycurl.Curl()
    head = ["Authorization: Bearer %s" % token]
    buffer = BytesIO()
    try:
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.HTTPHEADER, head)
        c.setopt(c.CONNECTTIMEOUT, 60)
        c.setopt(c.TIMEOUT, 600)
        c.perform()
        result = ansi_cleaner.sub("", buffer.getvalue().decode('utf-8'))
        c.close()
        buffer.close()
        return result
    except TypeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except IndentationError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except NameError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except pycurl.error as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1
    except json.decoder.JSONDecodeError as e:
        c.close()
        buffer.close()
        logger.error(traceback.format_exc(e))
        return 1

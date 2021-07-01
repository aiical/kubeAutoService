#!/usr/local/python374/bin/python3.7
# -*- coding: utf-8 -*-
import aiohttp
import aiofiles
import json


async def k8s_api_http_get(url, token, result_type):
    if result_type == 'json':
        content_type = "application/json"

    else:
        content_type = "text/html"

    headers = {
        "Content-Type": content_type,
        "Authorization": "Bearer %s" % token
    }
    async with aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=5)) as session:
        async with session.get(url) as resp:
            status = resp.status
            if result_type == 'json':
                body_json = await resp.json()
                return status, body_json
            else:
                body_text = await resp.text()
                return status, body_text


async def http_post(url, post_data):
    headers = {
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=5)) as session:
        async with session.post(url, data=json.dumps(post_data)) as resp:
            status = resp.status
            return status


async def harbor_api_http_get(url, username, password):
    auth = aiohttp.BasicAuth(login=username, password=password)
    headers = {
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession(
            headers=headers,
            auth=auth,
            timeout=aiohttp.ClientTimeout(total=5)) as session:
        async with session.get(url) as resp:
            status = resp.status
            body_json = await resp.json()
            return status, body_json


async def harbor_api_http_post(url, post_data, username, password):
    auth = aiohttp.BasicAuth(login=username, password=password)
    headers = {
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession(
            headers=headers,
            auth=auth,
            timeout=aiohttp.ClientTimeout(total=5)) as session:
        async with session.post(url, data=post_data) as resp:
            status = resp.status
            return status


async def get_file_func(url, params, filename):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as response:
            fa = await response.read()
            async with aiofiles.open(filename, mode='wb') as f:
                await f.write(fa)
                await f.close()


import sys
import os
import hashlib
import logging
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from qcloud_cos import CosServiceError
from qcloud_cos import CosClientError
from qcloud_cos.cos_threadpool import SimpleThreadPool
from const_define import *


def string_to_md5(file_name):
    m = hashlib.md5()
    m.update(file_name.encode('utf-8'))
    return m.hexdigest()

def upload_file_to_cos(task_id, file_path, choose_type):
    try:
        if choose_type != E_CHOOSE_IMG and choose_type != E_CHOOSE_VIDEO:
            return "", E_CHOOSE_TYPE_ERR
        REGION = 'ap-nanjing'      # 替换为用户的 region，已创建桶归属的region可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
        TOKEN = None               # 如果使用永久密钥不需要填入token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见https://cloud.tencent.com/document/product/436/14048
        SCHEME = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填
        config = CosConfig(Region=REGION, SecretId=COS_ID, SecretKey=COS_KEY, Token=TOKEN, Scheme=SCHEME)
        client = CosS3Client(config)
        file_key = E_COS_FILE_KEY + str(task_id) + "/" + string_to_md5(os.path.basename(file_path)) + ".jpg"
        if choose_type == E_CHOOSE_VIDEO:
            file_key = E_COS_FILE_KEY + str(task_id) + "/" + string_to_md5(os.path.basename(file_path)) + ".mp4"
        logging.info("[cos] upload file to oss! file_key: {} file_path: {}".format(file_key, file_path))
        # 上传由 '/' 分隔的对象名，自动创建包含文件的文件夹。想要在此文件夹中添加新文件时，只需要在上传文件至 COS 时，将 Key 填写为此目录前缀即可。
        with open(file_path, 'rb') as fp:
            response = client.put_object(
                Bucket=BUCKET_NAME,  # Bucket 由 BucketName-APPID 组成
                Body=fp,
                Key=file_key,
                StorageClass='STANDARD',
                Expires = '2592000'
                # ContentType='text/html; charset=utf-8'
            )
            print(response)
        # 获取URL
        url = client.get_object_url(
            Bucket=BUCKET_NAME,
            Key=file_key
        )
        print(url)
        logging.info("[cos] upload file to oss success! url: {}".format(url))
    except Exception as e:
        print(str(e))
        logging.error("[cos] upload file to oss failed! file_key: {} file_path: {} err: {}".format(file_key, file_path, str(e)))
        return "", E_COS_UPLOAD_ERROR
    return url, E_SUCESS

def download_file(file_key, output_path):

    # -*- coding=utf-8
    # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
    region = 'ap-nanjing'      # 替换为用户的 region，已创建桶归属的 region 可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
    token = None               # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
    scheme = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填
    config = CosConfig(Region=region, SecretId=COS_ID, SecretKey=COS_KEY, Token=token, Scheme=scheme)
    client = CosS3Client(config)
    response = client.get_object(
        Bucket=BUCKET_NAME,
        Key=file_key
    )
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    response['Body'].get_stream_to_file(output_path)


# upload_file_to_cos("templates/test", "/opt/facefusion-service/templates/AnimateDiff_00049/AnimateDiff_00049.mp4", E_CHOOSE_VIDEO)
# upload_file_to_cos("templates/test", "/opt/facefusion-service/templates/AnimateDiff_00049/AnimateDiff_00049.jpg", E_CHOOSE_IMG)
# download_file("face-swap/53231323/bd8d57c8f62825b3ef195e66b28b4b63.jpg", "/tmp/test.jpg")

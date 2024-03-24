import os
import logging
from typing import List, Optional, Any, Literal, Callable, Tuple, Dict, TypedDict
from facefusion.typing import LogLevel, VideoMemoryStrategy, FaceSelectorMode, FaceAnalyserOrder, FaceAnalyserAge, FaceAnalyserGender, FaceMaskType, FaceMaskRegion, OutputVideoEncoder, OutputVideoPreset, FaceDetectorModel, FaceRecognizerModel, TempFrameFormat, Padding

# 请求参数
# REQ_UUID  = "uuid"
# REQ_IMG64 = "img_base64"
# REQ_TEMPLATE = "req_template"
# REQ_TYPE = "req_type"

# 常量定义
# E_CHOOSE_IMG = "img"
# E_CHOOSE_VIDEO = "video"
E_USER_IMG_PATH = os.getcwd() + "/user_imgs"
E_TEMPLATE_PATH = os.getcwd() + "/templates"
E_OUTPUT_PATH = os.getcwd() + "/out_put"
E_COS_FILE_KEY = "out_put/"

# 套餐定义
E_CHOOSE_IMG = 1
E_CHOOSE_VIDEO = 2
# 处理状态定义
E_STATUS_TO_IMG = 1 # 照片待处理
E_STATUS_TO_VIDEO = 2 # 视频待处理
E_STATUS_PROCESSING = 3 # 处理中
E_STATUS_SUCCEEDED = 4 # 处理成功
E_STATUS_ERROR = 5 # 处理异常
# 模板状态定义
E_TEMPLATE_ADD = 1 # 待新增
E_TEMPLATE_DEL = 2 # 待删除
E_TEMPLATE_ADDED = 3 # 已新增
E_TEMPLATE_DELED = 4 # 已删除
E_TEMPLATE_PROCESSING = 5 # 处理中
E_TEMPLATE_ERROR = 6 # 处理异常

# MYSQL配置
MYSQL_HOST      = "sh-cynosdbmysql-grp-k2p5yn90.sql.tencentcdb.com"
MYSQL_PROT      = 20342
MYSQL_DATABASE  = "facefusion"
MYSQL_USR       = "root"
MYSQL_PWD       = "ubuntu@123G"

# cos配置
COS_ID = os.getenv("COS_ID")
COS_KEY = os.getenv("COS_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# 错误码
CODE = "code"
MSG = "msg"
E_SUCESS = {CODE:0, MSG:"success"}
E_BODY_NOT_JSON = {CODE:1001, MSG:"body is not json"}
E_REQ_UUID_ERR = {CODE:1002, MSG:"param uuid err"}
E_REQ_IMG64_ERR = {CODE:1003, MSG:"param img_base64 err"}
E_REQ_TEMPLATE_ERR = {CODE:1003, MSG:"param template err"}
E_CHOOSE_TYPE_ERR = {CODE:1003, MSG:"choose type err"}
E_READ_IMG64_ERR = {CODE:1003, MSG:"read img_base64 err"}
E_SAVE_IMG_ERR = {CODE:1004, MSG:"save img err"}
E_USER_IMG_PATH_ERR = {CODE:1005, MSG:"user img path err"}
E_TEMPLATE_IMG_PATH_ERR = {CODE:1006, MSG:"template img path err"}
E_TEMPLATE_VIDEO_PATH_ERR = {CODE:1007, MSG:"template video path err"}
E_OUTPUT_IMG_PATH_ERR = {CODE:1008, MSG:"output img path err"}
E_OUTPUT_VIDEO_PATH_ERR = {CODE:1009, MSG:"output img path err"}
E_OUTPUT_FRAMES_PATH_ERR = {CODE:1010, MSG:"output frames path err"}
E_NOT_FIND_TEMPLATE_FRAMES = {CODE:1010, MSG:"not find template frames"}
E_MERGE_VIDEO_ERR = {CODE:1010, MSG:"merge video err"}
E_PROCESS_VIDEO_ERR = {CODE:1010, MSG:"process video err"}
E_PROCESS_IMG_EXCEPTION = {CODE:1010, MSG:"process img exception"}
E_PROCESS_VIDEO_EXCEPTION = {CODE:1010, MSG:"process video exception"}
E_PROCESS_TEMPLATE_EXCEPTION = {CODE:1010, MSG:"process template exception"}
E_COS_UPLOAD_ERROR = {CODE:1010, MSG:"cos updload error"}
E_COS_IMG_DOWNLOAD_ERROR = {CODE:1010, MSG:"cos img download error"}
E_COS_VIDEO_DOWNLOAD_ERROR = {CODE:1010, MSG:"cos video download error"}
E_EXCEPTION_ERR = {CODE:9999, MSG:"exception err"}

class path_config:
    def __init__(self, uuid, req_template) -> None:
        uuid_str = str(uuid)
        self.user_path_list = []
        self.user_path_list.append(E_USER_IMG_PATH + "/" + uuid_str + ".jpg")
        self.template_path = E_TEMPLATE_PATH + "/" + req_template
        self.template_frame_path = self.template_path + "/frames"
        self.template_img_path = self.template_path + '/' + req_template + ".jpg"
        self.template_video_path = self.template_path + '/' + req_template + ".mp4"
        self.output_path = E_OUTPUT_PATH + "/" + uuid_str
        self.output_frame_path = self.output_path + "/frames"
        self.output_img_path = self.output_path + "/" + uuid_str + ".jpg"
        self.output_video_path = self.output_path + "/" + uuid_str + ".mp4"
        self.output_video_no_audio_path = self.output_path + "/" + uuid_str + "_no_audio.mp4"

        for user_path in self.user_path_list:
            user_dir = os.path.dirname(user_path)
            if not os.path.exists(user_dir):
                os.mkdir(user_dir)

        if not os.path.exists(self.template_path):
            return None
        if not os.path.exists(self.template_img_path):
            return None
        if not os.path.exists(self.template_video_path):
            return None
            # os.mkdir(self.template_path)

        if not os.path.exists(self.template_frame_path):
            os.mkdir(self.template_frame_path)

        if not os.path.exists(self.output_path):
            os.mkdir(self.output_path)

        if not os.path.exists(self.output_frame_path):
            os.mkdir(self.output_frame_path)

        logging.info(f'user_path:{self.user_path_list}')
        logging.info(f'template_img_path:{self.template_img_path}')
        logging.info(f'template_video_path:{self.template_video_path}')
        logging.info(f'template_frame_path:{self.template_frame_path}')
        logging.info(f'output_img_path:{self.output_img_path}')
        logging.info(f'output_frame_path:{self.output_frame_path}')
        logging.info(f'output_video_path:{self.output_video_path}')
        logging.info(f'output_video_no_audio_path:{self.output_video_no_audio_path}')

class template_info:
    def __init__(self) -> None:
        self.id = 0
        self.name = ""
        self.img_url = ""
        self.video_url = ""
        self.status = 0
        self.code = E_SUCESS[CODE]
        self.msg = E_SUCESS[MSG]
        self.img_path = ""
        self.video_path = ""
        self.img_file_key = ""
        self.video_file_key = ""


    def set_status(self, status, err):
        self.status = status
        self.code = err[CODE]
        self.msg = err[MSG]
    
    def get_dir(self):
        return E_TEMPLATE_PATH + "/" + self.name


class img_task_info:
    def __init__(self) -> None:
        self.id = 0
        self.choose_type = 0
        self.template_name = ""
        self.face = ""
        self.user_img_file_key = ""
        self.status = 0
        self.code = E_SUCESS[CODE]
        self.msg = E_SUCESS[MSG]
        self.fin_img_url = ""
        self.img_use_time = 0
        self.img_wait_time = 0
        self.create_time = 0
        
    def set_status(self, status, err):
        self.status = status
        self.code = err[CODE]
        self.msg = err[MSG]

class video_task_info:
    def __init__(self) -> None:
        self.id = 0
        self.choose_type = 0
        self.template_name = ""
        self.status = 0
        self.code = E_SUCESS[CODE]
        self.msg = E_SUCESS[MSG]
        self.fin_video_url = ""
        self.video_use_time = 0
        self.video_wait_time = 0
        self.create_time = 0
        
    
    def set_status(self, status, err):
        self.status = status
        self.code = err[CODE]
        self.msg = err[MSG]

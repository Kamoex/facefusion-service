from const_define import *
from facefusion import core
from facefusion import logger
from facefusion.processors.frame.core import get_frame_processors_modules
import facefusion.globals
import mysql_tools
import cos_tools
import traceback
import logging
import cv2
import base64
import numpy as np
import time
import shutil

def trace_info(e):
    logging.error("================================DEBUG_BEGIN================================")
    logging.error(traceback.format_exc())
    logging.error("================================DEBUG_END==================================")


def read_img_base64(base64_image: str):
    try:
        image_bytes = base64.b64decode(base64_image)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logging.error("read_img_base64 err: ", str(e))
    return None

class my_service:
    def __init__(self):
        # self.mod_param = mod_param()
        # self._user_cv_img = None
        logger.init("info")
        # 初始化参数和模型
        program = core.cli()
        core.apply_args(program)
        
    
    def run(self):
        while True:
            self.handle_template(E_TEMPLATE_ADD)
            self.handle_template(E_TEMPLATE_DEL)
            self.handle_photo()
            self.handle_viedo()
            time.sleep(2)
       
        # if photo_task is not None:
        #     # 获取路径信息
        #     path_info = path_config(photo_task.id, photo_task.template_name)
        # logging.info(f"request_id:{body[REQ_UUID]}, path init ok")
        # # 保存用户照片
        # cv2.imwrite(path_info.user_path_list[0], self._user_cv_img)
        # logging.info(f"request_id:{body[REQ_UUID]}, save user img ok")
        # # 检查路径
        # verify_res = self.verify_path(body[REQ_UUID], body[REQ_TYPE], path_info)
        # if verify_res[CODE] != E_SUCESS[CODE]:
        #     return verify_res
        # logging.info(f"request_id:{body[REQ_UUID]}, verify path ok")
        # # 模型处理
        # process_res = core.model_process(body[REQ_UUID], body[REQ_TYPE], path_info)
        # if process_res[CODE] != E_SUCESS[CODE]:
        #     return process_res
        # logging.info(f"request_id:{body[REQ_UUID]}, post_handle end")
        # return E_SUCESS
    
    def handle_template(self, status):
        template = mysql_tools.get_flag_template(status)
        if template is None:
            return
        try:
            # 新增模板
            if template.status == E_TEMPLATE_ADD:
                if len(template.video_path) > 0 and (cos_tools.download_file(template.video_file_key, template.video_path) == False):
                    template.set_status(E_TEMPLATE_ERROR, E_COS_VIDEO_DOWNLOAD_ERROR)
                    logging.error(f"[handle_template] id:{template.id}, cos video download error")
                    mysql_tools.update_template_task(template)
                    return
                if len(template.video_path) == 0 or (cos_tools.download_file(template.img_file_key, template.img_path) == False):
                    template.set_status(E_TEMPLATE_ERROR, E_COS_IMG_DOWNLOAD_ERROR)
                    logging.error(f"[handle_template] id:{template.id}, cos img download error")
                    mysql_tools.update_template_task(template)
                    return
                # 检查视频路径
                if not os.path.exists(template.video_path):
                    template.set_status(E_TEMPLATE_ERROR, E_TEMPLATE_VIDEO_PATH_ERR)
                    logging.error(f"[handle_template] id:{template.id}, video path not exists")
                    mysql_tools.update_template_task(template)
                    return
                # 检查图片路径
                if not os.path.exists(template.img_path):
                    template.set_status(E_TEMPLATE_ERROR, E_TEMPLATE_IMG_PATH_ERR)
                    logging.error(f"[handle_template] id:{template.id}, img path not exists")
                    mysql_tools.update_template_task(template)
                    return
                template.set_status(E_TEMPLATE_ADDED, E_SUCESS)
            # 删除模板
            elif template.status == E_TEMPLATE_DEL:
                if os.path.exists(template.get_dir()):
                    shutil.rmtree(template.get_dir())
                template.set_status(E_TEMPLATE_DELED, E_SUCESS)
            mysql_tools.update_template_task(template)
        except Exception as e:
            logging.error(f"[handle_template] id:{template.id}, exception: {str(e)}")
            template.set_status(E_TEMPLATE_ERROR, E_PROCESS_TEMPLATE_EXCEPTION)
            template.msg += " [exception]: " + traceback.format_exc()
            mysql_tools.update_template_task(template)
    
    def handle_photo(self):
        try:
            task:img_task_info = None 
            while True:
                start_time = time.time()
                # 获取待处理照片任务
                task = mysql_tools.get_photo_task()
                if task is None:
                    logging.info(f"[photo-processing] handle all task finish!")
                    break
                logging.info(f"[photo-processing] id:{task}, process begin")
                # 保存用户照片
                # user_cv_img = read_img_base64(task.face)
                # if user_cv_img is None:
                #     logging.error(f"[photo-processing] id:{task.id} read_img_base64 error!")
                #     task.set_status(E_STATUS_ERROR, E_READ_IMG64_ERR)
                #     mysql_tools.update_img_task(task)
                #     continue
                # logging.info(f"[photo-processing] id:{task.id}, read_img_base64 ok")
                # 获取路径信息
                path_info = path_config(task.id, task.template_name)
                cos_tools.download_file(task.user_img_file_key, path_info.user_path_list[0])
                # cv2.imwrite(path_info.user_path_list[0], self._user_cv_img)
                logging.info(f"[photo-processing] id:{task.id}, save photo ok")
                # 检查路径
                verify_res = self.verify_path(task.id, task.choose_type, path_info)
                if verify_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, verify_res)
                    logging.error(f"[photo-processing] id:{task.id} verify_path error!")
                    continue
                logging.info(f"[photo-processing] id:{task.id}, verify path ok")
                # 模型处理
                process_res = core.process_image(task.id, path_info, True)
                if process_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, process_res)
                    mysql_tools.update_img_task(task)
                    continue
                logging.info(f"[photo-processing] id:{task.id}, process_image ok")
                # 上传cos
                img_url, upload_res = cos_tools.upload_file_to_cos(task.id, path_info.output_img_path, E_CHOOSE_IMG)
                if upload_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, upload_res)
                    mysql_tools.update_img_task(task)
                    continue
                if task.choose_type == E_CHOOSE_IMG:
                    task.status = E_STATUS_SUCCEEDED
                else:
                    task.status = E_STATUS_TO_VIDEO
                task.fin_img_url = img_url
                task.img_use_time = round(time.time() - start_time, 2)
                task.img_wait_time = round(time.time() - task.create_time, 2)
                # 更新db
                mysql_tools.update_img_task(task)
                # 清除用户缓存
                if task.choose_type == E_CHOOSE_IMG and len(path_info.user_path_list) > 0:
                    os.remove(path_info.user_path_list[0])
                os.remove(path_info.output_img_path)
                logging.info(f"[photo-processing] id:{task.id}, clear cache ok")
                logging.info(f"[photo-processing] id:{task.id}, process end total use time {round(time.time() - start_time, 2)}s")
        except Exception as e:
            if task is not None:
                task.set_status(E_STATUS_ERROR, E_PROCESS_IMG_EXCEPTION)
                task.msg += " [exception]: " + traceback.format_exc()
                mysql_tools.update_img_task(task)
            trace_info(e)
    
    def handle_viedo(self):
        try:
            task = None 
            while True:
                start_time = time.time()
                # 获取待处理视频任务
                task = mysql_tools.get_video_task()
                if task is None:
                    logging.info(f"[video-processing] handle all task finish!")
                    break
                logging.info(f"[video-processing] id:{task.id}, process begin")
                # 获取路径信息
                path_info = path_config(task.id, task.template_name)
                # 检查路径
                verify_res = self.verify_path(task.id, task.choose_type, path_info)
                if verify_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, verify_res)
                    mysql_tools.update_video_task(task)
                    logging.error(f"[video-processing] id:{task.id} verify_path error!")
                    continue
                logging.info(f"[video-processing] id:{task.id}, verify path ok")
                # 模型处理
                process_res = core.process_video_new(task.id, path_info)
                if process_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, process_res)
                    mysql_tools.update_video_task(task)
                    continue
                logging.info(f"[video-processing] id:{task.id}, process_video_new ok")
                # todo 上传cos
                video_url, upload_res = cos_tools.upload_file_to_cos(task.id, path_info.output_video_path, E_CHOOSE_VIDEO)
                if upload_res[CODE] != E_SUCESS[CODE]:
                    task.set_status(E_STATUS_ERROR, upload_res)
                    mysql_tools.update_video_task(task)
                    continue
                # 更新db
                task.status = E_STATUS_SUCCEEDED
                task.fin_video_url = video_url
                task.video_use_time = round(time.time() - start_time, 2)
                task.video_wait_time = round(time.time() - task.create_time, 2)
                mysql_tools.update_video_task(task)
                # 清除用户缓存
                if len(path_info.user_path_list) > 0:
                    os.remove(path_info.user_path_list[0])
                shutil.rmtree(path_info.output_path)
                logger.info(f"[video-processing] id:{task.id}, process end total use time {round(time.time() - start_time, 2)}s")
        except Exception as e:
            if task is not None:
                task.set_status(E_STATUS_ERROR, E_PROCESS_VIDEO_EXCEPTION)
                task.msg += " [exception]: " + traceback.format_exc()
                mysql_tools.update_video_task(task)
            trace_info(e)


    # def post_handle(self, body):
    #     try:
    #         logging.info("post_handle begin")
    #         # 检测参数
    #         verify_res = self.verify_params(body) 
    #         if verify_res[CODE] != E_SUCESS[CODE]:
    #             return verify_res
    #         logging.info(f"request_id:{body[REQ_UUID]}, verify params ok")
    #         # 获取路径信息
    #         path_info = path_config(body[REQ_UUID], body[REQ_TEMPLATE])
    #         logging.info(f"request_id:{body[REQ_UUID]}, path init ok")
    #         # 保存用户照片
    #         cv2.imwrite(path_info.user_path_list[0], self._user_cv_img)
    #         logging.info(f"request_id:{body[REQ_UUID]}, save user img ok")
    #         # 检查路径
    #         verify_res = self.verify_path(body[REQ_UUID], body[REQ_TYPE], path_info)
    #         if verify_res[CODE] != E_SUCESS[CODE]:
    #             return verify_res
    #         logging.info(f"request_id:{body[REQ_UUID]}, verify path ok")
    #         # 模型处理
    #         process_res = core.model_process(body[REQ_UUID], body[REQ_TYPE], path_info)
    #         if process_res[CODE] != E_SUCESS[CODE]:
    #             return process_res
    #         logging.info(f"request_id:{body[REQ_UUID]}, post_handle end")
    #         return E_SUCESS
    #     except Exception as e:
    #         trace_info(e)
    
    # # 检查请求参数
    # def verify_params(self, body):
    #     if not isinstance(body, dict):
    #         return E_BODY_NOT_JSON
    #     if REQ_UUID not in body or not isinstance(body[REQ_UUID], str) or body[REQ_UUID] == '':
    #         return E_REQ_UUID_ERR
    #     if REQ_IMG64 not in body or not isinstance(body[REQ_IMG64], str) or body[REQ_IMG64] == '':
    #         return E_REQ_IMG64_ERR
    #     if REQ_TEMPLATE not in body or not isinstance(body[REQ_TEMPLATE], str) or body[REQ_TEMPLATE] == '':
    #         return E_REQ_TEMPLATE_ERR
    #     if REQ_TYPE not in body or not isinstance(body[REQ_TYPE], str) or body[REQ_TYPE] == '':
    #         return E_CHOOSE_TYPE_ERR
    #     self._user_cv_img = read_img_base64(body[REQ_IMG64])
    #     if self._user_cv_img is None:
    #         return E_READ_IMG64_ERR 
    #     return E_SUCESS
    
    # # 前处理
    # def pre_process(self, body) -> path_config:
    #     try:
    #         path = path_config(body[REQ_UUID], body[REQ_TEMPLATE])
    #         if path is None:
    #             return None
    #         # 保存图片
    #         cv2.imwrite(path.user_path_list[0], self._user_cv_img)
    #         return path
    #     except Exception as e:
    #         logging.error("save_img error: ", str(e))
    #         return None
    
    # 检查路径
    def verify_path(self, request_id, req_type, path_info: path_config):
        try:
            for user_path in path_info.user_path_list:
                if not os.path.exists(user_path):
                    return E_USER_IMG_PATH_ERR
            if not os.path.exists(path_info.template_img_path):
                return E_TEMPLATE_IMG_PATH_ERR
            if req_type == E_CHOOSE_VIDEO and not os.path.exists(path_info.template_video_path):
                return E_TEMPLATE_VIDEO_PATH_ERR
            if not os.path.exists(path_info.output_frame_path):
                return E_OUTPUT_FRAMES_PATH_ERR
            return E_SUCESS
        except Exception as e:
            logger.error(f"request_id: {request_id}, verify_path exception! " + str(e))
            return E_EXCEPTION_ERR

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    # with open("/opt/face-test/img/likui.jpeg", 'rb') as f:
    #     img_bytes = f.read()
    # base64_str = base64.b64encode(img_bytes).decode()
    # print(base64_str)
    service = my_service()
    service.run()

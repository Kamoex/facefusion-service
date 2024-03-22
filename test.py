import requests
import json
import time
import base64

# python3  run.py -s /opt/face-test/img/likui.jpeg -t /opt/face-test/video/1.mp4 -o /opt/face-test/video/1_res.mp4 --skip-download  --headless  --execution-providers cuda  --execution-thread-count 16 --execution-queue-count 8 --face-selector-mode one
def get_imgbase64(path):
    with open(path, 'rb') as f:
        img = f.read()
        return base64.b64encode(img).decode()
    
def test_post():
    # user_img = get_imgbase64("/home/zhanghe/tmp/face-test/img/likui.jpg")
    user_img = get_imgbase64("/opt/face-test/img/likui.jpeg")

    body = {
        "uuid":"456",
        "img_base64":user_img,
        "req_template":"AnimateDiff_00049",
        "req_type":"video"
    }
    # resp = requests.post(url = "http://127.0.0.1:5012", json=body)
    s = time.time()
    resp = requests.post(url = "http://127.0.0.1:7860", json=body)
    print(resp.text)
    print("use time: {:.2f}s".format(time.time() - s))

test_post()


# 视频检查 可以放在模板更新的时候检查
# if analyse_video(path_info.template_video_path, facefusion.globals.trim_frame_start, facefusion.globals.trim_frame_end):
#         return
# l


# docker cp 1c04ec3a848b:/opt/facefusion-service/const_define.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/facefusion.ini .
# docker cp 1c04ec3a848b:/opt/facefusion-service/mysql_tools.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/requirements.txt .
# docker cp 1c04ec3a848b:/opt/facefusion-service/cos_tools.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/install.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/run.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/test.py .
# docker cp 1c04ec3a848b:/opt/facefusion-service/facefusion .
# docker cp 1c04ec3a848b:/opt/facefusion-service/service.py .



import requests
import json
import time
import base64
import string
import random
import pymysql

def gen_rd_code():
    num_list = ['0','1','2','3','4','5','6','7','8','9']
    lower_liset = list(string.ascii_lowercase)
    origin_list = []
    res_list = []
    for i in range(4):
        code = list(string.ascii_lowercase)
        for j in range(10):
            code.append(str(j))
        origin_list.append(code)
    for c1 in origin_list[0]:
        for c2 in origin_list[1]:
            for c3 in origin_list[2]:
                if c1 == c2 and c2 == c3:
                    continue
                for c4 in origin_list[3]:
                    if c2 == c3 and c3 == c4:
                        continue
                    if c1 == c2 and c3 == c4:
                        continue
                    if c1 not in num_list and c2 not in num_list and c3 not in num_list and c4 not in num_list:
                        continue
                    if c1 not in lower_liset and c2 not in lower_liset and c3 not in lower_liset and c4 not in lower_liset:
                        continue
                    rd_code = (c1+c2+c3+c4, 0)
                    res_list.append(rd_code)
    random.shuffle(res_list)
    conn = pymysql.connect(host='sh-cynosdbmysql-grp-k2p5yn90.sql.tencentcdb.com', user='root', password='ubuntu@123G', database='facefusion', port=20342, charset='utf8')
    cursor = conn.cursor()
    cursor.executemany('insert into RandomCodes (rd_code, is_using) values(%s, %s)', res_list)
    conn.commit()
    


    

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

# test_post()
# gen_rd_code()


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



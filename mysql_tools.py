import pymysql
from const_define import *

g_db_conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USR, password=MYSQL_PWD, database=MYSQL_DATABASE, port=MYSQL_PROT, charset='utf8')

def check_db_conn(func):
    def wrapper(*args, **kwargs):
        try:
            g_db_conn.ping(reconnect=True)
        except Exception as e:
            raise ValueError("check db conn error! msg: " + str(e))
        return func(*args, **kwargs)
    return wrapper

@check_db_conn
def db_get_data():
    # 创建游标
    cursor = g_db_conn.cursor()
    # 执行SQL语句
    sql = "SELECT * FROM your_table"
    cursor.execute(sql)
    # 获取所有记录列表
    results = cursor.fetchall()
    for row in results:
        print(row)
    # 关闭游标
    cursor.close()

@check_db_conn
def get_photo_task() -> img_task_info:
    cursor = None
    task = None
    try:
        cursor = g_db_conn.cursor()
        g_db_conn.begin()
        cmd = f"SELECT id, choose_type, template_name, face, status, UNIX_TIMESTAMP(create_time) FROM Orders WHERE status = {E_STATUS_TO_IMG} LIMIT 1 FOR UPDATE"
        cursor.execute(cmd)
        res = cursor.fetchone()
        if res is not None:
            task = img_task_info()
            task.id = res[0]
            task.choose_type = res[1]
            task.template_name = res[2]
            task.face = res[3]
            task.status = res[4]
            task.create_time = res[5]
            img_url_split = task.face.split("myqcloud.com/")
            if len(img_url_split) > 1:
                task.user_img_file_key = img_url_split[1]
            cmd = f"UPDATE Orders SET status = {E_STATUS_PROCESSING} WHERE id = {task.id}"
            cursor.execute(cmd)
            g_db_conn.commit()
            # 拿到模板url给task设置上 如果处理失败 默认返回模板
            cmd = f"SELECT img_url FROM Templates WHERE name = '{task.template_name}'"
            cursor.execute(cmd)
            res = cursor.fetchone()
            if res is not None:
                task.fin_img_url = res[0]
        else:
            g_db_conn.commit()
            logging.info("[mysql] no img data need to process")
            cursor.close()
            return
        # 拿到4位随机码
        g_db_conn.begin()
        cmd = f"SELECT rd_code FROM RandomCodes WHERE is_using = 0 limit 1 FOR UPDATE"
        cursor.execute(cmd)
        res = cursor.fetchone()
        if res is not None:
            task.rd_code = res[0]
            cmd = f"UPDATE RandomCodes SET is_using = 1 WHERE rd_code='{task.rd_code}'"
        g_db_conn.commit()
        if len(task.rd_code) == 0:
            raise ValueError("rd_code is none")
    except Exception as e:
        logging.info("[mysql] get_photo_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    return task

@check_db_conn
def get_video_task() -> video_task_info:
    cursor = None
    task = None
    try:
        cursor = g_db_conn.cursor()
        g_db_conn.begin()
        cmd = f"SELECT id, choose_type, template_name, status, UNIX_TIMESTAMP(create_time) FROM Orders WHERE status = {E_STATUS_TO_VIDEO} LIMIT 1 FOR UPDATE"
        cursor.execute(cmd)
        res = cursor.fetchone()
        if res is not None:
            task = video_task_info()
            task.id = res[0]
            task.choose_type = res[1]
            task.template_name = res[2]
            task.status = res[3]
            task.create_time = res[4]
            cmd = f"UPDATE Orders SET status = {E_STATUS_PROCESSING} WHERE id = {task.id}"
            cursor.execute(cmd)
        else:
            logging.info("[mysql] no video data need to process")
        g_db_conn.commit()
        # 拿到模板url
        if task is not None:
            cmd = f"SELECT video_url FROM Templates WHERE name = '{task.template_name}'"
            cursor.execute(cmd)
            res = cursor.fetchone()
        if res is not None:
            task.fin_video_url = res[0]
    except Exception as e:
        logging.info("[mysql] get_video_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    return task

@check_db_conn
def update_img_task(task:img_task_info):
    cursor = None
    cmd = ""
    try:
        cursor = g_db_conn.cursor()
        cmd = f"UPDATE Orders SET status={task.status},code={task.code},msg='{task.msg}',fin_img_url='{task.fin_img_url}',rd_code='{task.rd_code}',img_use_time={task.img_use_time},img_wait_time={task.img_wait_time}  WHERE id={task.id}"
        cursor.execute(cmd)
        g_db_conn.commit()
    except Exception as e:
        logging.info("[mysql] update_img_task exception: " + str(e) + ", sql: " + cmd)
    if cursor is not None:
        cursor.close()

@check_db_conn
def update_video_task(task:video_task_info):
    cursor = None
    cmd = ""
    try:
        cursor = g_db_conn.cursor()
        cmd = f"UPDATE Orders SET status={task.status},code={task.code},msg='{task.msg}',fin_video_url='{task.fin_video_url}',video_use_time={task.video_use_time},video_wait_time={task.video_wait_time}  WHERE id={task.id}"
        cursor.execute(cmd)
        g_db_conn.commit()
    except Exception as e:
        logging.info("[mysql] update_img_task exception: " + str(e) + ", sql: " + cmd)
    if cursor is not None:
        cursor.close()

@check_db_conn
def get_flag_template(flag) -> template_info:
    cursor = None
    task = None
    try:
        cursor = g_db_conn.cursor()
        g_db_conn.begin()
        cmd = f"SELECT id, name, status, img_url, video_url FROM Templates WHERE status = {flag} LIMIT 1 FOR UPDATE"
        cursor.execute(cmd)
        res = cursor.fetchone()
        if res is not None:
            task = template_info()
            task.id = res[0]
            task.name = res[1]
            task.status = res[2]
            task.img_url = res[3]
            task.video_url = res[4]
            img_url_split = task.img_url.split("myqcloud.com/")
            if len(img_url_split) > 1:
                task.img_file_key = img_url_split[1]
                task.img_path = task.get_dir() + "/" + task.name + ".jpg"
            if len(task.video_url) > 0:
                video_url_split = task.video_url.split("myqcloud.com/")
                if len(video_url_split) > 1:
                    task.video_file_key = task.video_url.split("myqcloud.com/")[1]
                    task.video_path = task.get_dir() + "/" + task.name + ".mp4"
            cmd = f"UPDATE Templates SET status = {E_TEMPLATE_PROCESSING} WHERE id = {task.id}"
            cursor.execute(cmd)
        else:
            logging.info(f"[mysql] no template with status {flag} need to process")
        g_db_conn.commit()
    except Exception as e:
        logging.info("[mysql] template exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    return task

@check_db_conn
def update_template_task(task:template_info):
    cursor = None
    cmd = ""
    try:
        cursor = g_db_conn.cursor()
        cmd = f"UPDATE Templates SET status={task.status},code={task.code},msg='{task.msg}' WHERE id={task.id}"
        cursor.execute(cmd)
        g_db_conn.commit()
    except Exception as e:
        logging.info("[mysql] update_template_task exception: " + str(e) + ", sql: " + cmd)
    if cursor is not None:
        cursor.close()

@check_db_conn
def check_rd_code_valid():
    cursor = None
    cmd = ""
    try:
        cursor = g_db_conn.cursor()
        cmd = f"SELECT rd_code FROM Orders WHERE update_time < DATE_SUB(NOW(), INTERVAL 1 MONTH)"
        cursor.execute(cmd)
        res = cursor.fetchall()
        if res is None or len(res) == 0:
            cursor.close()
            return
        g_db_conn.begin()
        cmd = f"UPDATE Orders SET rd_code='' WHERE update_time < DATE_SUB(NOW(), INTERVAL 1 MONTH)"
        cursor.execute(cmd)
        cmd = "UPDATE RandomCodes SET is_using=0 WHERE rd_code=%s"
        cursor.executemany(cmd, res)
        g_db_conn.commit()
    except Exception as e:
        logging.info("check rd_code valid error! exception: " + str(e) + ", sql: " + cmd)
    if cursor is not None:
        cursor.close()
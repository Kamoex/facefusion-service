import pymysql
from const_define import *

def db_get_data():
    conn = pymysql.connect(host='localhost', user='root', password='your_password', database='your_database', charset='utf8')
    # 创建游标
    cursor = conn.cursor()
    # 执行SQL语句
    sql = "SELECT * FROM your_table"
    cursor.execute(sql)
    # 获取所有记录列表
    results = cursor.fetchall()
    for row in results:
        print(row)
    # 关闭游标和连接
    cursor.close()
    conn.close()

def get_photo_task() -> img_task_info:
    conn = None
    cursor = None
    task = None
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USR, password=MYSQL_PWD, database=MYSQL_DATABASE, charset='utf8')
        cursor = conn.cursor()
        conn.begin()
        cmd = f"SELECT id, choose_type, template_name, face, status, UNIX_TIMESTAMP(create_time) FROM {MYSQL_TAB} WHERE status = {E_STATUS_TO_IMG} LIMIT 1 FOR UPDATE"
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
            cmd = f"UPDATE {MYSQL_TAB} SET status = {E_STATUS_PROCESSING} WHERE id = {task.id}"
            cursor.execute(cmd)
        else:
            logging.info("[mysql] no img data need to process")
        conn.commit()
    except Exception as e:
        logging.info("[mysql] get_photo_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()
    return task


def get_video_task() -> video_task_info:
    conn = None
    cursor = None
    task = None
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USR, password=MYSQL_PWD, database=MYSQL_DATABASE, charset='utf8')
        cursor = conn.cursor()
        conn.begin()
        cmd = f"SELECT id, choose_type, template_name, status, UNIX_TIMESTAMP(create_time) FROM {MYSQL_TAB} WHERE status = {E_STATUS_TO_VIDEO} LIMIT 1 FOR UPDATE"
        cursor.execute(cmd)
        res = cursor.fetchone()
        if res is not None:
            task = video_task_info()
            task.id = res[0]
            task.choose_type = res[1]
            task.template_name = res[2]
            task.status = res[3]
            task.create_time = res[4]
            cmd = f"UPDATE {MYSQL_TAB} SET status = {E_STATUS_PROCESSING} WHERE id = {task.id}"
            cursor.execute(cmd)
        else:
            logging.info("[mysql] no video data need to process")
        conn.commit()
    except Exception as e:
        logging.info("[mysql] get_video_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()
    return task

def update_img_task(task:img_task_info):
    conn = None
    cursor = None
    task = None
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USR, password=MYSQL_PWD, database=MYSQL_DATABASE, charset='utf8')
        cursor = conn.cursor()
        cmd = f"UPDATE {MYSQL_TAB} SET status={task.status},code={task.code},msg={task.msg},fin_img_url={task.fin_img_url},img_use_time={task.img_use_time},img_wait_time={task.img_wait_time}  WHERE id={task.id}"
        cursor.execute(cmd)
        conn.commit()
    except Exception as e:
        logging.info("[mysql] update_img_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()

def update_video_task(task:video_task_info):
    conn = None
    cursor = None
    task = None
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USR, password=MYSQL_PWD, database=MYSQL_DATABASE, charset='utf8')
        cursor = conn.cursor()
        cmd = f"UPDATE {MYSQL_TAB} SET status={task.status},code={task.code},msg={task.msg},fin_video_url={task.fin_video_url},video_use_time={task.video_use_time},video_wait_time={task.video_wait_time}  WHERE id={task.id}"
        cursor.execute(cmd)
        conn.commit()
    except Exception as e:
        logging.info("[mysql] update_img_task exception: " + str(e))
        task = None
    if cursor is not None:
        cursor.close()
    if conn is not None:
        conn.close()
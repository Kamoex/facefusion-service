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
    pass

def get_video_task() -> video_task_info:
    pass

def update_task():
    pass
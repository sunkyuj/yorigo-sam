import os
import pymysql
import json
import requests
import boto3
import traceback
import base64


header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true",
}
# 초기화 관련 코드는 핸들러 밖에 빼는 것이 유리
conn = pymysql.connect(
    host=os.environ["RDS_ENDPOINT"],
    # host=os.environ["RDS_PROXY_ENDPOINT"],
    user=os.environ["RDS_USERNAME"],
    passwd=os.environ["RDS_PASSWD"],
    db=os.environ["RDS_DBNAME"],  # yorigo
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=120,
)
curs = conn.cursor()


def lambda_handler(event, context):
    print("## EVENT")
    print(event)

    # 상태코드값
    statusCodeVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감
        keyword = event["queryStringParameters"]["keyword"]

        statusCodeVal = 200
        # id가 존재할때는 id에 해당하는 아이템만 검색 아니면 전체 검색
        print("============ GET All Recipes ===============")
        sql = f"SELECT * FROM `recipe` WHERE recipe_title LIKE '%{keyword}%' OR recipe_foodname LIKE '%{keyword}%';"
        curs.execute(sql)
        bodyData = curs.fetchall()

        # else:

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(traceback.format_exc())
        bodyData = json.dumps(repr(e))

    finally:
        # 전달자료 변환
        print(bodyData)
        jsonData = json.dumps(bodyData, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결

    # client로 전송
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}

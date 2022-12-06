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


def lambda_handler(event, context):
    print("## EVENT")
    print(event)
    curs = conn.cursor()

    # 상태코드값
    statusCodeVal = 0
    # ID값
    idVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        statusCodeVal = 201
        idVal = event["pathParameters"]["id"]
        print("============ UPDATE Single Recipe ===============")
        recipe_query = f"UPDATE `recipe` SET  WHERE recipe_id = {idVal};"
        recipe_steps_query = (
            f"UPDATE `recipe` SET thumbnail_url = '{s3_base_url+thumbnail_key}' WHERE recipe_id = {recipe_id};"
        )
        sql = f"DELETE FROM `recipe` WHERE recipe_id={idVal};"
        curs.execute(sql)
        conn.commit()
        bodyData = "recipe updated"

        # else:
        #     statusCodeVal = 400
        #     print("========== UNSUPPORTED ROUTE ========== ")
        #     print(routeKeyVal)
        #     bodyData = "UNSUPPORTED ROUTE"

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


def get_as_base64(url):
    return base64.b64encode(requests.get(url).content)


def escape_name(s):
    """Escape name to avoid SQL injection and keyword clashes.

    Doubles embedded backticks, surrounds the whole in backticks.

    Note: not security hardened, caveat emptor.

    """
    return "`{}`".format(s.replace("`", "``"))

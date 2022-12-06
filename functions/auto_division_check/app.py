import os
import pymysql
import json
import requests
import boto3
import traceback
import base64
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true",
}
bucket_name = "yorigo-bucket"
region = "ap-northeast-2"
s3_base_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/"


def lambda_handler(event, context):
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

    print("## EVENT")
    print(event)
    curs = conn.cursor()

    # 상태코드값
    statusCodeVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        statusCodeVal = 200
        print("============ Auto Division Check ===============")
        requestJSON = json.loads(event["body"])  # dict
        print(type(requestJSON), requestJSON)
        if type(requestJSON) == str:
            print("requestJSON is str")
            requestJSON = json.loads(requestJSON)  # dict
        print(type(requestJSON), requestJSON)
        uuid = requestJSON["UUID"]
        print("uuid:", uuid)
        # query = f"SELECT * FROM `division_data`;"
        query = f'SELECT step_separated_times FROM `division_data` WHERE UUID = "{uuid}";'
        print("query: ", query)
        curs.execute(query)
        # step_separated_times = curs.fetchall()
        step_separated_times = curs.fetchone()
        print("step_separated_times: ", step_separated_times)

        if step_separated_times:
            bodyData = step_separated_times
            statusCodeVal = 200
        else:
            bodyData = "Video Division Still Processing"
            statusCodeVal = 204

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

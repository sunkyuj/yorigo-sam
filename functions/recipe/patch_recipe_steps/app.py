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
    if type(event) == str:
        print("event is str. changing tp dict")
        event = json.loads(event)
    print(event)
    curs = conn.cursor()

    # 상태코드값
    statusCodeVal = 0
    # ID값
    idVal = 0

    try:
        # event데이터 호출
        bodyData = json.loads(event["body"])  # body데이터 들어감
        if type(bodyData) == str:
            bodyData = json.loads(bodyData)  # body데이터 들어감

        print("bodyData:", bodyData)

        statusCodeVal = 201
        print("============ UPDATE Single Recipe ===============")
        # idVal = event["pathParameters"]["id"]
        recipe_id = bodyData["recipe_id"]
        step_separated_times = bodyData["step_separated_times"]
        if step_separated_times[0][0] == 0 and len(step_separated_times) >= 2:
            step_separated_times[1][1] = "00:00:00"  # step 1: start time is 0
            del step_separated_times[0]
        for step_no, step_start_time, step_end_time in step_separated_times:
            if step_no == 0:
                continue
            print(step_no, step_start_time, step_end_time)
            start_h, start_m, start_s = map(float, step_start_time.split(":"))
            start_int = int(start_h * 3600 + start_m * 60 + start_s)
            end_h, end_m, end_s = map(float, step_end_time.split(":"))
            end_int = int(end_h * 3600 + end_m * 60 + end_s)
            query = f"""UPDATE `recipe_steps` SET step_start_time = '{start_int}',  step_end_time = '{end_int}' 
                        WHERE (recipe_id = {recipe_id}) AND (step_no = {step_no});"""
            print(query)
            curs.execute(query)
        conn.commit()

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

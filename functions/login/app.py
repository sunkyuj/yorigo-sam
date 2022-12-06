import json
import boto3
import os

header = {"Content-Type": "application/json"}


def lambda_handler(event, context):
    print(event)

    user_id = event["body"]["user_id"]
    user_pw = event["body"]["user_pw"]

    # 상태코드값
    statusCodeVal = 0
    bodyData = ""

    try:
        statusCodeVal = 200  # 상태코드
        body = "login ok"

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(e)

    # finally:
    jsonData = json.dumps(body, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}

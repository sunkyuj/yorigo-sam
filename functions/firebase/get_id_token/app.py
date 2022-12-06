import os
import json
from firebase_admin import initialize_app, auth, db

# cred = credentials.Certificate(firebase_cred)
default_app = initialize_app()

header = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}


def lambda_handler(event, context):
    print("## EVENT")
    print(event)
    # 상태코드값
    statusCodeVal = 0
    bodyData = ""

    try:
        id_token = event["headers"]["Authorization"]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]
        bodyData = uid

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(e)

    finally:
        # 전달자료 변환
        print(bodyData)
        jsonData = json.dumps(bodyData, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결

    # client로 전송
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}

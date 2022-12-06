import os
import json
from firebase_admin import initialize_app, auth, db

# cred = credentials.Certificate(firebase_cred)
default_app = initialize_app()

header = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}


def lambda_handler(event, context):
    print("## EVENT")
    print(event)
    uid = event["uid"]
    # 상태코드값
    statusCodeVal = 0

    try:
        # event데이터 호출
        bodyData = ""  # body데이터 들어감

        statusCodeVal = 200
        # 아이템 단항목정보
        # idVal = event["pathParameters"]["id"]
        result = auth.get_user(uid)
        # auth.UserRecord.
        # print("meta:", result.display_name, result.user_metadata, result.toJSON())

        # dir = db.reference()  # 기본 위치 지정
        # print(dir.get())

        bodyData = result.email

        for user in auth.list_users().iterate_all():
            print("User: " + user.uid, user.display_name)
        # bodyData = dir

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

import os
import pymysql
import json
import boto3


# cred = credentials.Certificate(firebase_cred)

header = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}

# 초기화 관련 코드는 핸들러 밖에 빼는 것이 유리
conn = pymysql.connect(
    host=os.environ["RDS_ENDPOINT"],
    user=os.environ["RDS_USERNAME"],
    passwd=os.environ["RDS_PASSWD"],
    db=os.environ["RDS_DBNAME"],  # yorigo
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)


def lambda_handler(event, context):
    print("## EVENT")
    print(event)
    # asdf.f()
    curs = conn.cursor()

    # 라우터 키값
    if "routeKey" in event:
        routeKeyVal = event["routeKey"]
    else:
        routeKeyVal = event["requestContext"]["resourceId"]

    # 상태코드값
    statusCodeVal = 0
    # ID값
    idVal = 0

    try:
        # event데이터 호출
        bodyData = ""  # body데이터 들어감

        # 라우터 키값에 따라 실행
        if routeKeyVal == "GET /user":
            statusCodeVal = 200
            # id가 존재할때는 id에 해당하는 아이템만 검색 아니면 전체 검색
            print("============ GET All Users ===============")
            sql = "select * from `user`"
            curs.execute(sql)
            bodyData = curs.fetchall()

        elif routeKeyVal == "GET /user/{id}":
            statusCodeVal = 200
            # 아이템 단항목정보
            idVal = event["pathParameters"]["id"]
            print("============ GET Single User with idVal ===============")

            # id_token = event["Authorization"]
            # decoded_token = auth.verify_id_token(id_token)
            # print(decoded_token)

            bert_lambda = boto3.client("lambda")
            response = bert_lambda.invoke(
                FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:yorigo-sam-YorigoFirebaseFucntion-MXW3VV69Ebpr",
                InvocationType="RequestResponse",
                # InvocationType="Event",
                Payload=json.dumps({"uid": "pfddgGtvZ5atn8Fp6utoVBk0KBn1"}),
            )
            # print(auth.UidIdentifier("pfddgGtvZ5atn8Fp6utoVBk0KBn1"))
            # result = auth.get_user("pfddgGtvZ5atn8Fp6utoVBk0KBn1")
            # print("email:", result.email)
            # bodyData = result.email
            print(response)
            response = response["Payload"].read().decode()
            response = json.loads(response)
            print(response)
            bodyData = response

        elif routeKeyVal == "POST /user":
            statusCodeVal = 201
            print("============ POST Single User ===============")
            # requestJSON = event["body"]  # {"user_uid":5000}
            requestJSON = json.loads(event["body"])  # {"user_uid":5000}
            # requestJSON = json.loads(event)  # {"user_uid":5000}
            # requestJSON = event  # {"user_uid":5000}
            print(requestJSON)  # dict
            userData = {
                "user_idname": requestJSON["uid"],
                "user_nickname": requestJSON["displayName"],
                "user_password": "",
                "user_name": requestJSON["displayName"],
                "user_register_date": requestJSON["metadata"]["creationTime"],
                "user_email": requestJSON["email"],
                "user_profile_image": requestJSON["photoURL"],
                "firebase_uid": requestJSON["uid"],
            }

            names = list(userData)
            cols = ", ".join(map(escape_name, names))  # assumes the keys are *valid column names*.
            placeholders = ", ".join(["%({})s".format(name) for name in names])

            query = "INSERT INTO `user` ({}) VALUES ({})".format(cols, placeholders)
            curs.execute(query, userData)
            conn.commit()
            bodyData = "user uploaded"

        elif routeKeyVal == "DELETE /user":
            statusCodeVal = 201
            print("============ DELETE Single User ===============")
            requestBody = json.loads(event["body"])  # {"user_uid":5000}
            # idVal = event["pathParameters"]["id"]
            user_name = requestBody["displayName"]
            firebase_uid = requestBody["uid"]
            print("firebase_uid: ", firebase_uid)
            sql = f'DELETE FROM `user` WHERE firebase_uid = "{firebase_uid}";'
            print(sql)
            curs.execute(sql)
            conn.commit()
            bodyData = f"username {user_name} is deleted"

        else:
            statusCodeVal = 400
            print("========== UNSUPPORTED ROUTE ========== ")
            print(routeKeyVal)
            bodyData = "UNSUPPORTED ROUTE"

    # except Exception as e:
    #     statusCodeVal = 400
    #     print("============ ERROR ===============")
    #     print(e)
    #     print(repr(e))

    finally:
        # 전달자료 변환
        print(bodyData)
        jsonData = json.dumps(bodyData, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결

    # client로 전송
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}


def escape_name(s):
    """Escape name to avoid SQL injection and keyword clashes.

    Doubles embedded backticks, surrounds the whole in backticks.

    Note: not security hardened, caveat emptor.

    """
    return "`{}`".format(s.replace("`", "``"))

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
    # asdf.f()
    print("conn:", conn)
    curs = conn.cursor()
    print("curs:", curs)

    # 라우터 키값
    # if "routeKey" in event:
    #     routeKeyVal = event["routeKey"]
    # else:
    #     routeKeyVal = event["requestContext"]["resourceId"]

    # 상태코드값
    statusCodeVal = 0
    # ID값
    idVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        # 라우터 키값에 따라 실행
        # if routeKeyVal == "POST /recipe/{id}/comment":
        statusCodeVal = 201
        print("============ POST Recipe Comment ===============")
        requestJSON = json.loads(event["body"])
        requestJSON["user_uid"] = get_user_uid(curs, event["headers"]["authorization"])

        print(requestJSON)  # dict

        names = list(requestJSON)
        cols = ", ".join(map(escape_name, names))  # assumes the keys are *valid column names*.
        placeholders = ", ".join(["%({})s".format(name) for name in names])

        query = "INSERT INTO `recipe_comment` ({}) VALUES ({})".format(cols, placeholders)
        curs.execute(query, requestJSON)
        conn.commit()
        bodyData = "comment uploaded"

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


def get_user_uid(curs, token):
    firebase_lambda = boto3.client("lambda")
    response = firebase_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:yorigo-sam-YorigoFirebaseGetUserFucntion-EfbeGQ8WoVeG",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=json.dumps({"token": token}),
    )
    print("response: 👉️", response)  # response: 👉️ <Response [204]>
    payload = response["Payload"].read().decode()  # str
    print("response payload type: 👉️", type(payload))
    user_data = json.loads(payload)
    print("user data:", user_data["body"])
    firebase_uid = user_data["body"]  # "xmA2OLL1t8TaYxxr6z0yXiwhy9s2" 이런식으로 따옴표가 붙어서 나옴

    query = f"SELECT `user_uid` FROM `user` where firebase_uid={firebase_uid};"
    print(query)
    curs.execute(query)
    conn.commit()
    # bodyData = "recipe uploaded"
    user_uid = curs.fetchone()["user_uid"]
    # print("type of user_uid: ", type(user_uid))  # int
    return user_uid

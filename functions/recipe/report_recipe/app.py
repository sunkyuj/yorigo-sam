import os
import pymysql
import json
import boto3


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
    curs = conn.cursor()

    # 상태코드값
    statusCodeVal = 0

    try:
        # event데이터 호출
        bodyData = ""  # body데이터 들어감

        # 라우터 키값에 따라 실행
        statusCodeVal = 200
        print("============ Report Recipe ===============")
        # user_uid = get_user_uid(curs, event["headers"]["authorization"])
        report_target_id = event["pathParameters"]["id"]

        report_query = f"update `recipe` set recipe_reported = recipe_reported+1 where recipe_id ={report_target_id}"
        curs.execute(report_query)
        # 레시피 작성자도 신고 1회?

        conn.commit()
        bodyData = f"reported user {report_target_id}"

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(e)
        print(repr(e))

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
    user_uid = curs.fetchone()["user_uid"]
    return user_uid

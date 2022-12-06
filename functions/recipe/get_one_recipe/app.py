import os
import pymysql
import json
import boto3
import traceback


header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true",
}


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
    # ID값
    idVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        # if routeKeyVal == "GET /recipe/{id}":
        statusCodeVal = 200
        # 아이템 단항목정보
        idVal = event["pathParameters"]["id"]
        print("============ GET Single Recipe with idVal ===============")
        print("GET Recipe with idVal=" + idVal)

        # 레시피
        add_view_query = f"update `recipe` set recipe_views = recipe_views+1 where recipe_id ={idVal}"
        curs.execute(add_view_query)
        recipe_query = f"select * from `recipe` where recipe_id={idVal}"
        curs.execute(recipe_query)
        bodyData = curs.fetchone()
        print(type(bodyData))
        if bodyData["recipe_steps"]:
            bodyData["recipe_steps"] = json.loads(bodyData["recipe_steps"])  # 역슬래쉬 제거

        # 레시피 단계
        recipe_steps_query = f"select * from `recipe_steps` where recipe_id={idVal}"
        curs.execute(recipe_steps_query)
        bodyData["recipe_steps"] = curs.fetchall()
        bodyData["recipe_comment"] = get_recipe_comments(curs, event)

        # print(bodyData["recipe_comment"])
        # # 댓글
        # comment_query = f"select * from `recipe_comment` rc where rc.recipe_id={idVal} "
        # if "authorization" in event["headers"]:
        #     user_uid = get_user_uid(curs, event["headers"]["authorization"])
        #     comment_query += f"""
        #     AND rc.user_uid NOT IN (
        #         select blocker_uid from `block` where blocked_uid = {user_uid}
        #         UNION DISTINCT
        #         select blocked_uid from `block` where blocker_uid = {user_uid}
        #     )
        #     """
        # curs.execute(comment_query)
        # bodyData["recipe_comment"] = curs.fetchall()
        # conn.commit()
        print(bodyData)

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(traceback.format_exc())
        bodyData = json.dumps(repr(e))

    finally:
        # 전달자료 변환
        print(bodyData)
        jsonData = json.dumps(bodyData, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결

        # curs.close()
        conn.close()

    # client로 전송
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}


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
    # bodyData = "recipe uploaded"
    user_uid = curs.fetchone()["user_uid"]
    # print("type of user_uid: ", type(user_uid))  # int
    return user_uid


def get_recipe_comments(curs, event):
    recipe_comments_lambda = boto3.client("lambda")
    response = recipe_comments_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:yorigo-sam-YorigoGetRecipeComment-QVK8V9HT79u1",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=json.dumps({"headers": event["headers"], "pathParameters": event["pathParameters"]}),
    )
    print("response: 👉️", response)  # response: 👉️ <Response [204]>
    payload = response["Payload"].read().decode()  # str
    print("response payload type: 👉️", type(payload))
    recipe_comments = json.loads(payload)
    print("recipe_comments:", type(recipe_comments["body"]))
    return json.loads(recipe_comments["body"])

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

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        statusCodeVal = 201
        print("============ POST Single Recipe ===============")
        requestJSON = json.loads(event["body"])  # dict
        requestJSON["user_uid"] = get_user_uid(curs, event["headers"]["authorization"])
        recipe_steps = requestJSON.pop("recipe_steps", None)
        requestJSON.pop("video_length", 0)
        total_steps = len(recipe_steps)

        # s3 = boto3.resource("s3") # for s3 upload via server
        s3 = boto3.client("s3")  # for presigned url
        step_explanations = []
        step_time = 0
        for step in recipe_steps:  # type of step: dict
            step["step_timers"] = []  # create step_timers in requestJSON
            if "step_separated_times" in step:
                start_str, end_str = step["step_separated_times"].split("-")
                start_int, end_int = time_to_int(start_str), time_to_int(end_str)
                step["step_start_time"] = start_int
                step["step_end_time"] = end_int
            # 2. reshaping for model
            step_explanations.append(step["step_explanation"])

        # 3. invoke bert-model-lambda

        recipe_explanations = json.dumps({"recipe_explanations": step_explanations})  # str
        print(recipe_explanations)
        recipe_ingredients, recipe_tools, time_info = invoke_model(recipe_explanations)

        ingredient_lambda_response = invoke_ingredient_lambda(recipe_ingredients)
        print(ingredient_lambda_response)
        tool_lambda_response = invoke_tool_lambda(recipe_tools)
        print(tool_lambda_response)

        for t in time_info:
            step_number, step_timer = t[0], t[1]
            print("requestJSON[recipe_steps][step_number]'s type:", type(recipe_steps[step_number - 1]))
            recipe_steps[step_number - 1]["step_timers"].append(step_timer)

        requestJSON["recipe_ingredients"] = json.dumps(recipe_ingredients)
        requestJSON["recipe_tools"] = json.dumps(recipe_tools)

        query = make_query("INSERT INTO `recipe` ({}) VALUES ({});", names=list(requestJSON))
        curs.execute(query, requestJSON)
        recipe_id = curs.lastrowid
        print("recipe_id:", recipe_id)

        # # sqs
        # sqs = boto3.client("sqs")
        # sqs_response = sqs.send_message(
        #     QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/972644607073/sqs-demo",
        #     MessageBody=json.dumps(
        #         {
        #             "recipe_explanations": step_explanations,
        #             "video_url": requestJSON["video_url"],
        #             "recipe_title": requestJSON["recipe_title"],
        #             "recipe_id": recipe_id,
        #         }
        #     ),
        # )
        # print("sqs:", sqs_response)

        thumbnail_key = f"static/recipe/{requestJSON['user_uid']}/{recipe_id}/thumbnail.jpeg"
        presigned_urls = [
            generate_presigned_url(
                s3,
                "put_object",
                {"Bucket": bucket_name, "Key": f"static/recipe/{requestJSON['user_uid']}/{recipe_id}/thumbnail.jpeg"},
                1000,
            )
        ]
        query = f"UPDATE `recipe` SET thumbnail_url = '{s3_base_url+thumbnail_key}' WHERE recipe_id = {recipe_id};"
        curs.execute(query)

        recipe_steps_query = "INSERT INTO `recipe_steps` VALUES (%s,%s,%s,%s,%s,%s,%s)"
        recipe_steps_val = []
        for step_no in range(1, total_steps + 1):
            file_name_with_extention = f"static/recipe/{requestJSON['user_uid']}/{recipe_id}/step_img{step_no}.jpeg"
            step_photo_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name_with_extention}"
            recipe_steps[step_no - 1]["step_photo_url"] = step_photo_url  # 나중에 지울듯

            presigned_url = generate_presigned_url(
                s3,
                "put_object",
                {"Bucket": bucket_name, "Key": file_name_with_extention},  # key가 폴더가 될 수 있나?
                1000,
            )
            presigned_urls.append(presigned_url)
            recipe_steps_val.append(
                (
                    recipe_id,
                    step_no,
                    recipe_steps[step_no - 1]["step_explanation"],
                    step_photo_url,
                    json.dumps(recipe_steps[step_no - 1]["step_timers"]),
                    recipe_steps[step_no - 1]["step_start_time"],
                    recipe_steps[step_no - 1]["step_end_time"],
                )
            )
        curs.executemany(recipe_steps_query, recipe_steps_val)
        conn.commit()
        # bodyData = requestJSON
        bodyData = presigned_urls

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


def make_query(q: str, names: list):
    cols = ", ".join(map(escape_name, names))  # assumes the keys are *valid column names*.
    placeholders = ", ".join(["%({})s".format(name) for name in names])

    query = q.format(cols, placeholders)
    print(cols)
    print(placeholders)
    print(query)
    return query


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


def invoke_model(recipe_explanations):
    print("invoke model!")
    bert_lambda = boto3.client("lambda")
    model_response = bert_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:lambda-docker-ner-image",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=recipe_explanations,
    )

    try:
        model_response = json.loads(model_response["Payload"].read().decode())
        print(type(model_response["body"]), model_response["body"])  # str
        response_body = json.loads(model_response["body"])
        print(type(response_body), response_body)  # dict
        model_result = response_body["result"]
        print(type(model_result), model_result)  # dict

    except Exception as e:
        print("============ MODEL ERROR ===============")
        print(traceback.format_exc())
        print(json.dumps(repr(e)))
        return ([], [], [])

    recipe_ingredients = model_result["ingredient"]
    recipe_tools = model_result["tool"]
    time_info = model_result["time"]
    print("recipe_ingredients:", recipe_ingredients)  # list
    print("recipe_tools:", recipe_tools)  # list
    print("time_info:", time_info)  # list

    return (recipe_ingredients, recipe_tools, time_info)


def invoke_ingredient_lambda(ingredients):
    print("invoke ingredient lambda!")
    req = {"routeKey": "POST /ingredient", "ingredients": ingredients}
    ingredient_lambda = boto3.client("lambda")
    response = ingredient_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:yorigo-sam-YorigoIngredient-D9k30oiE1YeL",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=json.dumps(req),
    )

    return json.loads(response["Payload"].read().decode())


def invoke_tool_lambda(tools):
    print("invoke tool lambda!")
    req = {"routeKey": "POST /tool", "tools": tools}
    tool_lambda = boto3.client("lambda")
    response = tool_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:yorigo-sam-YorigoTool-SAJQyuwqeocn",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=json.dumps(req),
    )

    return json.loads(response["Payload"].read().decode())


def generate_presigned_url(s3_client, client_method, method_parameters, expires_in):
    """
    Generate a presigned Amazon S3 URL that can be used to perform an action.

    :param s3_client: A Boto3 Amazon S3 client.
    :param client_method: The name of the client method that the URL performs.
    :param method_parameters: The parameters of the specified client method.
    :param expires_in: The number of seconds the presigned URL is valid for.
    :return: The presigned URL.
    """
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod=client_method, Params=method_parameters, ExpiresIn=expires_in
        )
        logger.info("Got presigned URL: %s", url)
    except ClientError:
        logger.exception("Couldn't get a presigned URL for client method '%s'.", client_method)
        raise
    return url


def time_to_int(time_str: str):
    time_str = time_str.strip()
    h, m, s = map(float, time_str.split(":"))
    time_int = int(h * 3600 + m * 60 + s)
    return time_int

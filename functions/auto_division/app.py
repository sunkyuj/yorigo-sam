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


def lambda_handler(event, context):
    print("## EVENT")
    print(event)

    # 상태코드값
    statusCodeVal = 0

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        statusCodeVal = 202
        print("============ Auto Division Request ===============")
        requestJSON = json.loads(event["body"])  # dict
        # requestJSON["user_uid"] = get_user_uid(curs, event["headers"]["authorization"])
        recipe_steps = requestJSON.pop("recipe_steps", None)

        step_explanations = []
        for step in recipe_steps:  # type of step: dict
            # 2. reshaping for model
            step_explanations.append(step["step_explanation"])

        recipe_explanations = json.dumps({"recipe_explanations": step_explanations})  # str
        print(recipe_explanations)

        # sqs
        sqs = boto3.client("sqs")
        sqs_response = sqs.send_message(
            QueueUrl="https://sqs.ap-northeast-2.amazonaws.com/972644607073/sqs-demo",
            MessageBody=json.dumps(
                {
                    "UUID": requestJSON["UUID"],
                    "recipe_explanations": step_explanations,
                    "video_url": requestJSON["video_url"],
                    "recipe_title": requestJSON["recipe_title"],
                    # "recipe_id": recipe_id,
                }
            ),
        )
        print("sqs:", sqs_response)

        # bodyData = requestJSON

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

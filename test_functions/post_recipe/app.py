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

# 초기화 관련 코드는 핸들러 밖에 빼는 것이 유리
conn = pymysql.connect(
    host=os.environ["RDS_ENDPOINT"],
    # host=os.environ["RDS_PROXY_ENDPOINT"],
    user=os.environ["RDS_USERNAME"],
    passwd=os.environ["RDS_PASSWD"],
    db="test",  # yorigo
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=120,
)
bucket_name = "yorigo-bucket"
region = "ap-northeast-2"


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
        # requestJSON["user_uid"] = get_user_uid(curs, event["headers"]["authorization"])
        requestJSON["user_uid"] = 5014
        recipe_steps = requestJSON["recipe_steps"]  # list
        total_steps = len(recipe_steps)

        # s3 = boto3.resource("s3") # for s3 upload via server
        s3 = boto3.client("s3")  # for presigned url
        step_explanations = []
        step_images = []
        for step in recipe_steps:  # type of step: dict
            step["step_timers"] = []  # create step_timers in requestJSON

            # # 1. upload image files to s3
            # upload_img_to_s3(
            #     s3=s3,
            #     user_uid=requestJSON["user_uid"],
            #     requestId=event["requestContext"]["requestId"],
            #     step=step,
            # )

            step_images.append((step["step_no"], step["step_image"]))
            step.pop("step_image", None)  # after upload, delete the real size img

            # 2. reshaping for model
            step_explanations.append(step["step_explanation"])

        # 3. invoke bert-model-lambda
        recipe_explanations = json.dumps({"recipe_explanations": step_explanations})  # str
        recipe_ingredients, recipe_tools, time_info = invoke_model(recipe_explanations)

        for t in time_info:
            step_number, step_timer = t[0], t[1]
            print("requestJSON[recipe_steps][step_number]'s type:", type(requestJSON["recipe_steps"][step_number]))
            requestJSON["recipe_steps"][step_number]["step_timers"].append(step_timer)

        requestJSON["recipe_steps"] = json.dumps(requestJSON["recipe_steps"])
        requestJSON["recipe_ingredients"] = json.dumps(recipe_ingredients)
        requestJSON["recipe_tools"] = json.dumps(recipe_tools)

        names = list(requestJSON)
        cols = ", ".join(map(escape_name, names))  # assumes the keys are *valid column names*.
        placeholders = ", ".join(["%({})s".format(name) for name in names])

        query = "INSERT INTO `recipe_test` ({}) VALUES ({});".format(cols, placeholders)
        print(query)
        curs.execute(query, requestJSON)
        recipe_id = curs.lastrowid
        print("recipe_id:", recipe_id)

        requestJSON["recipe_steps"] = json.loads(requestJSON["recipe_steps"])

        presigned_urls = []
        for step_no in range(total_steps):
            file_name_with_extention = f"static/recipe/{requestJSON['user_uid']}/{recipe_id}_img{step_no+1}.jpeg"
            step_photo_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name_with_extention}"
            requestJSON["recipe_steps"][step_no]["step_photo_url"] = step_photo_url

            presigned_url = generate_presigned_url(
                s3,
                "put_object",
                {"Bucket": bucket_name, "Key": file_name_with_extention},
                1000,
            )
            presigned_urls.append(presigned_url)

        # for step_no, step_image in step_images:
        #     img_url = upload_img_to_s3(
        #         s3=s3,
        #         user_uid=requestJSON["user_uid"],
        #         recipe_id=recipe_id,
        #         step_no=step_no,
        #         step_image=step_image,
        #     )
        #     requestJSON["recipe_steps"][step_no - 1]["step_photo_url"] = img_url

        requestJSON["recipe_steps"] = json.dumps(requestJSON["recipe_steps"])
        query = (
            f"UPDATE `recipe_test` SET recipe_steps = '{requestJSON['recipe_steps']}' WHERE recipe_id = {recipe_id};"
        )
        print(query)
        curs.execute(query)
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


def upload_img_to_s3(s3, user_uid, recipe_id, step_no, step_image):
    if step_image:
        # file_name_with_extention = "recipe_step_images/{}_img{}.jpeg".format(requestId, step_no)
        file_name_with_extention = f"static/recipe/{user_uid}/{recipe_id}_img{step_no}.jpeg"
        obj = s3.Object(bucket_name, file_name_with_extention)
        print("obj:", obj)
        try:
            decoded_img = base64.b64decode(step_image, validate=True)
            print("decoded:", decoded_img)
            obj.put(Body=decoded_img)  # obj.put time out
            print("put ok")
            return file_name_with_extention
            # step["step_photo_url"] = file_name_with_extention

        except Exception as e:
            print("============ Invalid Image ERROR ===============")
            print(repr(e))

    return ""


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

    query = f"SELECT `user_uid` FROM `user_test` where firebase_uid={firebase_uid};"
    print(query)
    curs.execute(query)
    conn.commit()
    # bodyData = "recipe uploaded"
    user_uid = curs.fetchone()["user_uid"]
    # print("type of user_uid: ", type(user_uid))  # int
    return user_uid


def invoke_model(recipe_explanations):
    print("invoke!")
    bert_lambda = boto3.client("lambda")
    model_response = bert_lambda.invoke(
        FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:lambda-docker-ner-image",
        InvocationType="RequestResponse",
        # InvocationType="Event",
        Payload=recipe_explanations,
    )

    model_response = json.loads(model_response["Payload"].read().decode())
    print(type(model_response["body"]), model_response["body"])  # str
    response_body = json.loads(model_response["body"])
    print(type(response_body), response_body)  # dict
    model_result = response_body["result"]
    print(type(model_result), model_result)  # dict

    recipe_ingredients = model_result["ingredient"]
    recipe_tools = model_result["tool"]
    time_info = model_result["time"]
    print("recipe_ingredients:", recipe_ingredients)
    print("recipe_tools:", recipe_tools)
    print("time_info:", time_info)

    return (recipe_ingredients, recipe_tools, time_info)


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

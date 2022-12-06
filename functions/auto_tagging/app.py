import os
import json
import boto3
import traceback
import logging

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

        statusCodeVal = 201
        print("============ POST Single Recipe ===============")
        requestJSON = json.loads(event["body"])  # dict
        recipe_steps = requestJSON["recipe_steps"]

        # s3 = boto3.resource("s3") # for s3 upload via server
        step_explanations = []
        for step in recipe_steps:  # type of step: dict
            step["step_timers"] = []  # create step_timers in requestJSON
            # 2. reshaping for model
            step_explanations.append(step["step_explanation"])

        # 3. invoke bert-model-lambda

        recipe_explanations = json.dumps({"recipe_explanations": step_explanations})  # str
        print(recipe_explanations)
        recipe_ingredients, recipe_tools, time_info = invoke_model(recipe_explanations)

        for t in time_info:
            step_number, step_timer = t[0], t[1]
            print("requestJSON[recipe_steps][step_number]'s type:", type(recipe_steps[step_number - 1]))
            recipe_steps[step_number - 1]["step_timers"].append(step_timer)

        requestJSON["recipe_ingredients"] = json.dumps(recipe_ingredients, ensure_ascii=False)
        requestJSON["recipe_tools"] = json.dumps(recipe_tools, ensure_ascii=False)

        bodyData = requestJSON

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

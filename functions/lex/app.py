import json
import boto3
import os

header = {"Content-Type": "application/json"}


def lambda_handler(event, context):
    print(event)
    user_input_json = json.loads(event["body"])  # 사용자가 말한 정보가 들어있는 json (dict)
    user_input_text = user_input_json["text"]  # 텍스트로 변환된 사용자 음성
    print(user_input_text)

    # 라우터 키값
    # routeKeyVal = event["routeKey"]
    # 상태코드값
    statusCodeVal = 0
    bodyData = ""

    try:

        statusCodeVal = 200  # 상태코드

        # LexV2 client uses 'lexv2-runtime'
        client = boto3.client("lexv2-runtime")
        print(os.environ["BOT_ID"], os.environ["BOT_ALIAS_ID"])
        response = client.recognize_text(
            botId=os.environ["BOT_ID"],
            botAliasId=os.environ["BOT_ALIAS_ID"],
            localeId="ko_KR",
            # sessionId=event["requestContext"]["requestId"], # Member must satisfy regular expression pattern: [0-9a-zA-Z._:-]+
            sessionId="test_session",
            text=user_input_text,  # 사용자가 말한 내용 전달
        )
        print(response)  # type: dict
        best_intent = response["interpretations"][0]
        intent_name = best_intent["intent"]["name"]

        if intent_name == "CallYorigo":
            body = {"command": "call_yorigo"}

        elif intent_name == "Search":
            body = {
                "command": "search",
                "searchValue": best_intent["intent"]["slots"]["Food"]["value"]["interpretedValue"],
            }

        elif intent_name == "VideoControll":
            body = {"command": best_intent["intent"]["slots"]["SimpleCommand"]["value"]["interpretedValue"]}

        elif intent_name == "VideoTimeControll":
            # t = 5  # 나중에 슬롯 값으로 수정
            timeValue = best_intent["intent"]["slots"]["CommandTime"]["value"]["interpretedValue"]
            body = {
                "command": best_intent["intent"]["slots"]["TimeRequiredCommand"]["value"]["interpretedValue"],
                "time": timeValue,
            }

        elif intent_name == "FallbackIntent":
            pass
            body = "FallbackIntent"
            # body = "안녕하세요 사용자님"
        else:
            body = "no matching intent"

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(e)
        body = e

    # finally:
    jsonData = json.dumps(body, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}

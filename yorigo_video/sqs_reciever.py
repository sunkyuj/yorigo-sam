import boto3, json, requests
import handler

queue_url = "https://sqs.ap-northeast-2.amazonaws.com/972644607073/sqs-demo"
sqs_client = boto3.client(service_name="sqs", region_name="ap-northeast-2")
lambda_client = boto3.client(service_name="lambda", region_name="ap-northeast-2")


def handle_sqs():
    # sqs message recieve
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=5,  # 최대 5초 기다려보고 없으면 ec2 종료
        AttributeNames=["All"],
    )
    print(type(response))  # dict
    print(response)

    if "Messages" not in response:
        print("sqs is empty")
        return
        #     # ec2 off
        #     lambda_client.invoke(
        #         FunctionName="arn:aws:lambda:ap-northeast-2:972644607073:function:StopEC2Instances",
        #     )

        # exit()

    for message in response["Messages"]:
        bodyData = json.loads(message["Body"])
        print(type(bodyData))  # dict
        print(bodyData["video_url"])

        try:
            # send to model and get segment
            result = handler.main(
                bodyData["recipe_explanations"],
                bodyData["video_url"],
                bodyData["recipe_title"],
            )  # video division process
            print(result)

            if "recipe_id" in bodyData:  # update
                recipe_update(bodyData["recipe_id"], result)

            elif "UUID" in bodyData:  # add to db
                store_division_data(bodyData["UUID"], result)

        except Exception as e:
            print(e)
            print("error")

        # sqs message delete
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])


def recipe_update(recipe_id, step_separated_times):

    payload = {"recipe_id": recipe_id, "step_separated_times": step_separated_times}

    # recipe update
    print("invoke lambda")
    res = requests.patch(
        url=f"https://1bzul9draj.execute-api.ap-northeast-2.amazonaws.com/recipe/{recipe_id}",
        json=json.dumps(payload),
    )
    print(res.status_code)


def store_division_data(UUID, step_separated_times):
    payload = {"UUID": UUID, "step_separated_times": step_separated_times}

    # store division_data to db
    print("invoke lambda")
    res = requests.post(
        url=f"https://1bzul9draj.execute-api.ap-northeast-2.amazonaws.com/store-division-data",
        json=json.dumps(payload),
    )
    print(res.status_code)


while True:
    print("handle sqs")
    handle_sqs()

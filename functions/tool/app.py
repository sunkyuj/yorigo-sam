import os
import pymysql
import json
import boto3
import traceback


# 초기화 관련 코드는 핸들러 밖에 빼는 것이 유리
conn = pymysql.connect(
    host=os.environ["RDS_ENDPOINT"],
    # host=os.environ["RDS_PROXY_ENDPOINT"],
    user=os.environ["RDS_USERNAME"],
    passwd=os.environ["RDS_PASSWD"],
    db=os.environ["RDS_DBNAME"],  # yorigo
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

header = {"Content-Type": "application/json"}


def lambda_handler(event, context):
    # CloudWatch LogGroup에서 확인하기 위한 환경 및 이벤트내용 출력 (실제운영시에는 제외)
    print("## EVENT")
    print(event)

    curs = conn.cursor()

    # 라우터 키값
    routeKeyVal = event["routeKey"]
    # 상태코드값
    statusCodeVal = 0

    # ID값
    idVal = 0

    try:
        # 상태코드
        statusCodeVal = 200
        # event데이터 호출
        bodyData = ""  # body데이터 들어감

        # 라우터 키값에 따라 실행
        if routeKeyVal == "GET /tool":
            # id가 존재할때는 id에 해당하는 아이템만 검색 아니면 전체 검색
            print("============ GET All tool ===============")
            sql = "select * from tool"
            curs.execute(sql)
            bodyData = curs.fetchall()

        elif routeKeyVal == "GET /tool/{id}":
            # 아이템 단항목정보
            idVal = event["pathParameters"]["id"]
            print("============ GET Single tool with idVal ===============")
            print("GET Ingredient with idVal=" + idVal)
            sql = f"select * from tool where tool_id={idVal}"
            curs.execute(sql)
            bodyData = curs.fetchone()

        elif routeKeyVal == "POST /tool":
            tools = event["tools"]
            res = []
            for tool in tools:
                try:
                    sql = "INSERT INTO `tool` (`tool_name`) VALUES (%s);"
                    print(sql)
                    curs.execute(sql, tool)
                    res.append(f"{tool} is inserted into tool db")
                except pymysql.err.IntegrityError as e:
                    print(e.args)
                    res.append(e.args)
            conn.commit()
            bodyData = res

        else:
            print("========== UNSUPPORTED ROUTE ========== ")
            print(routeKeyVal)
            bodyData = "UNSUPPORTED ROUTE"

    except Exception as e:
        statusCodeVal = 400
        print("============ ERROR ===============")
        print(e)
        print(traceback.format_exc())
        bodyData = json.dumps(repr(e))

    else:
        statusCodeVal = 201
    finally:
        # 전달자료 변환
        # OLD  jsonData = json.dumps(bodyData) # json형태 한글깨짐
        print(bodyData)
        jsonData = json.dumps(bodyData, ensure_ascii=False, default=str).encode("utf8")  # 한글깨짐문제 해결

    # client로 전송
    return {"headers": header, "statusCode": statusCodeVal, "body": jsonData}

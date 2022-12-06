import os
import pymysql
import json
import traceback
import logging

logger = logging.getLogger(__name__)


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

    try:
        # event데이터 호출
        bodyData = {}  # body데이터 들어감

        statusCodeVal = 201
        print("============ Auto Division Data Store ===============")
        requestJSON = json.loads(event["body"])  # dict
        print(type(requestJSON), requestJSON)
        if type(requestJSON) == str:
            print("requestJSON is str")
            requestJSON = json.loads(requestJSON)  # dict
        print(type(requestJSON), requestJSON)
        requestJSON["step_separated_times"] = json.dumps(requestJSON["step_separated_times"])

        query = make_query("INSERT INTO `division_data` ({}) VALUES ({});", names=list(requestJSON))
        curs.execute(query, requestJSON)
        conn.commit()
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
    print(query)
    return query

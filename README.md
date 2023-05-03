![image](https://user-images.githubusercontent.com/38223044/235896003-10688ec4-8de9-444d-8f00-f750021f544d.png)

- 백엔드 아키텍처 설계
    - AWS 클라우드 서비스를 활용한 서버리스 아키텍쳐 구현 및 백엔드 인프라 설계
    - AWS Lambda 내 각 기능별로 독자적인 배포가 가능한 MSA 구조
        - API 서버 구축: API Gateway + AWS Lambda
        - 빠른 개발, 적은 비용, 높은 확장성의 이유로 해당 구조로 설계하기로 결정
        - Swagger를 이용한 REST API 문서화
            
    - 데이터베이스 구조 설계
        
![image](https://user-images.githubusercontent.com/38223044/235896276-8ef5bf58-9fa2-44ba-ba5b-dd958794dba9.png)
        
    
- 인공지능 학습 데이터 확보 및 영상분할 파이프라인 구축
    - 데이터 크롤링
        - 약 1만개의 레시피 데이터 크롤링
        - 식재료, 음식 데이터 크롤링
        - 각 데이터를 JSON화 하여 인공지능 학습 데이터 확보
    - 영상 분할 파이프라인 구축
        - **Lambda의 실행시간 제한 문제 우회**
            1. 영상 분할 작업은 많은 시간을 소요하기 때문에 Lambda만으로는 처리할 수 없음
            2. 영상 업로드 시 SQS에 영상 정보 전송
            3. sqs_reciever에서 주기적으로 SQS 메세지 fetch
            4. GPU가 탑재된 EC2에서 영상 분할 처리
            5. 영상 분할 후 DB에 분할 정보 업데이트

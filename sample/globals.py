
from datetime import datetime
import sqlite3
from typing import Dict, TypedDict
import requests
from dotenv import load_dotenv
import os
from telegram.ext import (
    ApplicationBuilder,
)

load_dotenv()

class AccountDict(TypedDict):
    acc_num: str # 계좌번호
    method_id: str # 메소드 id


class T0424Dict(TypedDict):
    expcode: str
    hname: str  # 종목명
    mdposqt: int # 매도가능수량
    sunikrt: float  # 수익율
    top_sunikrt: float # 최고 수익률
    addup_cnt: int # 애드업 갯수
    trailing_rate: float # 트레일링 구간


class T8436Dict(TypedDict):
    shcode: str # 종목코드
    hname: str # 종목명
    market: str # kospi or kosdaq

class T8410Dict(TypedDict):
    shcode: str # 종목코드
    hname: str # 종목명

class AccDict(TypedDict):
    accnum: str # 계좌번호
    name: str # 계좌명
    detail: str # 상세설명


class MethodDict(TypedDict):
    method_id: str # 메소드 코드
    detail: str # 상세설명
    accnum: str # 연관 계좌번호


class PassedDict(TypedDict):
    shcode: str # 종목코드
    method_id: str # 투자 방법
    addup_rate: float # 애드업 기준 수익률
    addup_cnt: float # 애드업 횟수
    top_sunikrt: float # 최고 수익률
    trailing_rate: float # 트레일링스탑 비율
    mdposqt: int # 매도가능수량
    create_date: datetime # 시간타입
    status: str # "no": 거래없음, "account": 보유중, "complete": 매매완료


class LS_vars:
    telegram_token = os.getenv('TELEGRAM-TOKEN')
    chat_id = os.getenv('TELEGRAM-CHAT-ID')
    telegram_app = ApplicationBuilder().token(telegram_token).build()

    ### 예수금 ###
    cspaq12200_event = None
    cspaq12200_telegram_requesting = True # 텔레그램으로 요청
    cspaq12200_whileloop = True
    cspaq12200_renew = False # 예수금 갱신여부 
    Dps = 0 # 100% 주문가능 금액

    ### 계좌잔고 ###
    t0424_event = None
    t0424_telegram_requesting = True
    t0424_whileloop = True

    ### 국내주식 ###
    t8410_event = None
    t8410_whileloop = False
    korea_drate = 0.0 # 국내장 추세 비율
    korea_drate_pass = False # 국내장 통과 여부
    code_drate = 0.0 # 개별 종목 추세 비율
    code_days = 0 # 주시하려는 일자수
    code_gubun = "2" # 2:일, 3:주, 4:월, 차트 수신 구간에서 공휴일을 제외하는데 사용된다.
    code_drate_pass = True # 개별 종목 통과 여부
    month_scodes: list[T8410Dict] = [] # 월 단위 추세 통과된 종목 목록
    week_scodes: list[T8410Dict] = [] # 주 단위 추세 통과된 종목 목록
    day_scodes: list[T8410Dict] = [] # 일 단위 추세 통과된 종목 목록
    day_short_scodes: list[T8410Dict] = [] # 일 단기 단위 추세 통과된 종목 목록
    
    ### 해외주식 ###
    g3204_event = None
    g3204_whileloop = False
    america_drate = 10.0 # 미국장 추세 비율
    america_drate_pass = False # 미국장 추세 통과 여부

    ### 종목들 ###
    t8436_event = None
    t8436_scodes: list[T8436Dict] = []
    t8436_whileloop = True

    ### 종목 현재가 ###
    t8407_event = None
    t8407_repeat_cnt = 1 # 반복요청 횟수

    ### 주문 ###
    cspat00600_event = None

    ### 주문 체결 ###
    sc1_event = None

### 텔레그램 url 전송 ###
def send_telegram(text):
    url = (
        f"https://api.telegram.org/bot{LS_vars.telegram_token}/sendMessage?chat_id={LS_vars.chat_id}&text={text}"
    )
    requests.get(url)
#####

### 날짜 datetime으로 변환 ###
def convert_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()
#####

### 데이터베이스 초기 세팅 ###
conn = sqlite3.connect("C:/sqlite_db/stock_db.db")
conn.row_factory = sqlite3.Row  # row_factory를 Row로 설정하면 딕셔너리처럼 사용 가능
sqlite3.register_converter("DATE", convert_date) # sqlite table에 날짜 타입을 저장할때의 기본 형태 구성
cursor = conn.cursor()
#####


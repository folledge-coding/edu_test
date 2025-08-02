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

class StockPositionDict(TypedDict):
    shcode: str  # 종목코드
    hname: str   # 종목명
    qty: int     # 보유수량
    avg_price: int  # 평균단가
    current_price: int  # 현재가
    today_low: int     # 당일 저가
    profit_rate: float # 수익률
    sell_3_qty: int    # 3% 매도 수량
    sell_5_qty: int    # 5% 매도 수량 
    sell_7_qty: int    # 7% 매도 수량
    sell_3_done: bool  # 3% 매도 완료 여부
    sell_5_done: bool  # 5% 매도 완료 여부
    sell_7_done: bool  # 7% 매도 완료 여부
    low_updated: bool  # 저가 갱신 여부
    status: str        # active, stop_loss, completed

class OrderDict(TypedDict):
    shcode: str     # 종목코드
    order_type: str # sell_3, sell_5, sell_7, stop_loss
    order_id: str   # 주문번호
    qty: int        # 주문수량
    price: int      # 주문가격
    is_completed: bool # 체결완료 여부

class LS_vars:
    telegram_token = os.getenv('TELEGRAM-TOKEN')
    chat_id = os.getenv('TELEGRAM-CHAT-ID')
    telegram_app = ApplicationBuilder().token(telegram_token).build()

    ### 보유종목 관리 ###
    stock_positions: Dict[str, StockPositionDict] = {}  # 종목코드별 포지션 정보
    pending_orders: Dict[str, OrderDict] = {}  # 대기중인 주문 정보
    
    ### 예수금 ###
    cspaq12200_event = None
    cspaq12200_whileloop = True
    Dps = 0  # 예수금

    ### 계좌잔고 ###
    t0424_event = None
    t0424_whileloop = True

    ### 현재가 조회 ###
    t8407_event = None
    t8407_whileloop = True

    ### 주문 관련 ###
    cspat00600_event = None  # 주식주문
    cspat00800_event = None  # 주식정정주문

    ### 실시간 데이터 ###
    sc0_event = None   # 실시간 주식체결
    sc1_event = None   # 실시간 주문체결

    ### 시스템 상태 ###
    is_market_open = False
    last_check_time = None

### 텔레그램 메시지 전송 ###
def send_telegram(text):
    url = (
        f"https://api.telegram.org/bot{LS_vars.telegram_token}/sendMessage?chat_id={LS_vars.chat_id}&text={text}"
    )
    try:
        requests.get(url)
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")

### 날짜 datetime으로 변환 ###
def convert_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()

### 데이터베이스 초기 세팅 ###
conn = sqlite3.connect("C:/sqlite_db/auto_trading_db.db")
conn.row_factory = sqlite3.Row
sqlite3.register_converter("DATE", convert_date)
cursor = conn.cursor()

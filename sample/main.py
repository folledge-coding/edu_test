import asyncio
from remote.pg_telegram import telegram_init
from globals import LS_vars, send_telegram, cursor
from ls_res.login import Login_req
from ls_res.cspaq12200 import Cspaq1220_req
from ls_res.t0424 import T0424_req
from ls_res.t8407 import T8407_req
from ls_res.t8436 import T8436_req
from ls_res.sc1 import SC1_req
import pythoncom
from datetime import datetime
from methods.turtle import Method_req
from database.stock_db import createStocksTable, insertStocks
from database.account_db import insertAccounts, createAccountsTable, createTempOrderingStocksTable
from database.method_db import countPassedAccountedStocks, insertMethods, getPassedStocksNotTrading, createMethodsTable, createPassedStockTable
import sys

async def main():

    ## 텔레그램과 로그인 세팅 ##
    await telegram_init()
    Login_req().req()
    #####
    #####
    
    ## 데이터베이스부터 최초 생성 ##
    createStocksTable()
    createAccountsTable()
    createMethodsTable()
    createPassedStockTable()
    createTempOrderingStocksTable()
    #####
    #####

    ### 테이블에 기본 정보 삽입 ##
    await T8436_req.req()
    insertStocks(LS_vars.t8436_scodes)

    insertAccounts(
        [{"accnum":"20250183601", "name":"추세추종 계좌", "detail":"장기 추세의 종목들만 거래하는 계좌이다."}]
    )

    insertMethods(
        [
            {"method_id":"turtle", "detail":"추세추종 종목 추출하기", "accnum": "20250183601"},
            {"method_id":"app", "detail":"증권앱에서 따로 주문 넣은 경우", "accnum": "20250183601"}    
        ]
    )
    #####
    #####

    ## 주시 가능한 가장 최근 종목들 가져오기 ##
    passedes = getPassedStocksNotTrading()

    send_telegram(
        f"""
오늘 주시할 종목 갯수: {len(passedes)}
"""
    )
    #####
    #####

    ## 잔고 세팅 ##
    SC1_req.req()
    await Cspaq1220_req.req()
    await T0424_req.req()
    #####
    #####

    ## 반복 루프 돌리기 ##
    asyncio.create_task(Cspaq1220_req.loop())
    asyncio.create_task(T0424_req.loop())
    #####
    #####

    send_telegram("🤖 모든 세팅을 완료했습니다. 주식장은 저에게 맡겨주시고 편하게 쉬세요!")

    ## 시간 체크 ##
    asyncio.create_task(start_time_check())
    asyncio.create_task(end_time_check())
    #####
    #####

    while True:
        await asyncio.sleep(0.01)
        pythoncom.PumpWaitingMessages()


async def start_time_check():
    '''
    09:01 - 종목 거래 들어감
    '''
    start_hour = 9
    start_min = 1

    while True:
        now = datetime.now()
        if now.hour == start_hour and now.minute == start_min:
            await T8407_req.req()

            break

        await asyncio.sleep(1)  # 1초 대기


async def end_time_check():
    '''
    18:00 - 장마감 후 종목 분석

    분석 완료되면 프로그램 종료
    '''
    end_hour = 18
    end_min = 0

    while True:
        now = datetime.now()
        if now.hour >= end_hour and now.minute >= end_min:
            send_telegram("장 종료 후, 종목 추출 계산 시작")

            # 새로운 종목 업로드 및 계산
            await Method_req.calculator()

            # 종목계산 완료 후 파이썬 종료
            send_telegram("🤖 모든 분석을 끝냈습니다. 오늘도 수고하셨습니다.")

            # DB 연결 끊음
            cursor.close()
            
            # 프로그램 종료
            # 다음날에는 윈도우의 스케줄러로 자동 실행
            sys.exit()

            break

        await asyncio.sleep(1)  # 1초 대기

if __name__ == "__main__":
    print("PROGRAM GARDEN")
    send_telegram("🤖 좋은 아침입니다! 자동화매매 시스템을 세팅하겠습니다.")

    asyncio.run(main())

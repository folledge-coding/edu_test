
import asyncio
from math import floor
from dotenv import load_dotenv
import win32com.client
from globals import LS_vars, send_telegram
from ls_res.cspat00600 import Cspat00600_req
from database.method_db import (
    countPassedAccountedStocks, 
    getPassedStocksNotTrading, 
    getPassedStock,
)
import random
import os

load_dotenv()

class T8407_res:
    def OnReceiveData(xingApi, szCode):

        if LS_vars.t8407_repeat_cnt > 5:
            send_telegram(
f"""
🚨 장시작 종목 주문이 5번 반복 요청 됐지만,
최종적으로 주문이 들어가지지 않았습니다.
코드에 문제가 있을 수 있습니다.
"""
            )
            return


        if LS_vars.cspaq12200_renew == False:
                
            send_telegram(
f"""
🚨 예수금이 세팅되어 있지 않아서
장시작하고 종목들이 주문들어가지지 않았습니다.
{LS_vars.t8407_repeat_cnt}번째 재주문을 시작했습니다.
"""
            )

            LS_vars.t8407_repeat_cnt += 1

            T8407_req.req()

            return

        # 최대 5개까지만 사도록 분할매매
        upto = 5
        cnt = countPassedAccountedStocks()
        upto = upto - cnt
        
        # 예수금의 60%만 거래에 사용
        amt = round(LS_vars.Dps * 0.6, 0)
        # 5개 종목은 살 수 있게 나눔
        amt = amt / upto

        cnt = xingApi.GetBlockCount("t8407OutBlock1")
        hnames = []
        for i in range(cnt):
            shcode = xingApi.GetFieldData("t8407OutBlock1", "shcode", i)
            hname = xingApi.GetFieldData("t8407OutBlock1", "hname", i)
            offerho = int(xingApi.GetFieldData("t8407OutBlock1", "offerho", i)) #매도호가

            # 이미 보유하고 있는지 확인한다.
            passedStock = getPassedStock(shcode, "account")
            mExist = passedStock.get("shcode", None)

            # 보유 중이면 구매 안함
            if mExist is not None :
                continue

            # 시장가로 주문 넣을 것이니깐, 매도호가로 구매수량 계산한다.
            qty = floor(amt / offerho)
            if qty > 0:

                # 시장가 매수 주문
                Cspat00600_req.order(
                    accnum=os.getenv('LS-ACC'), 
                    IsuNo=shcode, 
                    BnsTpCode="2",
                    OrdQty=qty,
                    hname=hname,
                )
                
                # 텔레그램에 보내야해서 리스트로 잠시 담음
                hnames.append(hname)

                # 10개까지만 구매
                if i == upto:
                    break

        # 주문후 바뀐 예수금으로 갱신 기다리기
        LS_vars.cspaq12200_renew = False

        send_telegram(
f"""
== 주문 신청한 종목들 ==
총 {len(hnames)}개

{", ".join(hnames)}
"""
        )

class T8407_req:
    
    async def req():
        """
        주시하는 종목들 정보를 확인해서 거래에 들어간다.
        장 시작 후 딱 한번만 실행됨으로 예수금이 미리 세팅되어 있어야 한다.
        """

        await asyncio.sleep(5)
        
        pass_stocks = getPassedStocksNotTrading()

        send_telegram(f"분석으로 추출된 {len(pass_stocks)}개 종목들 정보 요청")

        if len(pass_stocks) == 0:
            return
        
        # 리스트를 랜덤으로 섞어준다.
        random.shuffle(pass_stocks)

        cnt = 0
        shcode_list = []
        for stock in pass_stocks:
            shcode = stock["shcode"]

            if cnt > 40:
                break

            cnt += 1
            shcode_list.append(shcode)

        if LS_vars.t8407_event is None:
            LS_vars.t8407_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", T8407_res)
            LS_vars.t8407_event.ResFileName = "C:/LS_SEC/xingAPI/Res/t8407.res"

        LS_vars.t8407_event.SetFieldData("t8407InBlock", "nrec", 0, cnt)
        LS_vars.t8407_event.SetFieldData("t8407InBlock", "shcode", 0, ''.join(shcode_list))
        LS_vars.t8407_event.Request(False)

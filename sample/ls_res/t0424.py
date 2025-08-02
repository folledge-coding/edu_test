import asyncio
from typing import Dict
import win32com.client
from globals import LS_vars, PassedDict, T0424Dict, send_telegram
from database.method_db import updatePassedOnlyTrailing, updatePassedOnlyStatus, insertPassedStock, getPassedStock
from database.account_db import getTempOrderingStock, deleteTempOrderingStock
from dotenv import load_dotenv
import os
from ls_res.cspat00600 import Cspat00600_req
import pythoncom

load_dotenv()

class T0424_res:

    def OnReceiveData(xingApi, szCode):

        # 예수금이 갱신 되어야한다.
        if LS_vars.cspaq12200_renew == False:
            LS_vars.t0424_whileloop = False

            return

        t0424_codes: Dict[str, T0424Dict] = {}
        cnt = xingApi.GetBlockCount("t0424OutBlock1")
        for i in range(cnt):
            expcode: str = xingApi.GetFieldData("t0424OutBlock1", "expcode", i)  # 종목번호
            mdposqt = xingApi.GetFieldData("t0424OutBlock1", "mdposqt", i)  # 매도가능수량
            mdposqt = int(mdposqt)
            hname = xingApi.GetFieldData("t0424OutBlock1", "hname", i)  # 종목명
            price = xingApi.GetFieldData("t0424OutBlock1", "price", i)  # 현재가
            price = int(price)
            sunikrt = xingApi.GetFieldData("t0424OutBlock1", "sunikrt", i)  # 수익율
            sunikrt = float(sunikrt)

            ### 증권앱에서 별도로 주문했을 경우, table에 존재하는지 확인 ###
            passdedStock = getPassedStock(expcode)
            existStatus = passdedStock.get("status", None)
            if existStatus is None:
                # 존재 안하면 삽입해주기
                insertPassedStock({
                    "method_id":"app",
                    "shcode": expcode,
                    "status": "account"
                })

            elif existStatus == "no":
                # 거래한적 없다고 저장되어 있다면, 보유종목으로 업데이트 해주기
                updatePassedOnlyStatus(
                    shcode=expcode,
                    status="account"
                )
            #####
            
            ### 이전 주문이 완료되지 않았는지 확인 ###
            tempStock = getTempOrderingStock(expcode)
            tempShcode = tempStock.get("shcode", None)

            ## 매도가능수량이 0인 경우 패쓰 ##
            if mdposqt == 0:
                continue

                # 매도가능수량이 존재하고 주문 신청 중인 경우에는
                # 이전 주문신청 테이블에서 안 지워진 것임으로 지우기
                # *우리는 시장가 전량매매만 한다. 그러므로 매도가능수량은 주문 넣고나면 무조건 0이다.
            elif mdposqt > 0 and tempShcode is not None:
                deleteTempOrderingStock(expcode)

                # 이전 주문이 아직 남아있는 경우 패쓰 
            elif tempShcode is not None:
                continue
            #####


            ## 해당 종목이 보유중으로 저장되어 있는지 DB에서 가져오기 ##
            passdedStock = getPassedStock(expcode, "account")
            passdedStock:PassedDict = passdedStock or {}
            
            addup_rate = passdedStock.get("addup_rate", 30.0)
            addup_cnt = passdedStock.get("addup_cnt", 0)
            trailing_rate = passdedStock.get("trailing_rate", -5.0)
            top_sunikrt = passdedStock.get("top_sunikrt", 0.0)
            #####

            ## 최고 수익률 갱신과 트레일링스탑 비율 업데이트 ##
            if top_sunikrt < sunikrt:
                top_sunikrt = sunikrt
                
                trailing_rate = T0424_res.calculate_sell_point(
                    profit_rate=top_sunikrt
                )

                updatePassedOnlyTrailing(
                    shcode=expcode,
                    top_sunikrt=top_sunikrt,
                    trailing_rate=trailing_rate,
                )
            #####

            ## 현재 수익률이 트레일링스탑 밑으로 떨어졌을 때 전량 매도 ##
            if mdposqt > 0 and trailing_rate > sunikrt:
                
                # 매도하기
                Cspat00600_req.order(
                    accnum=os.getenv('LS-ACC'),
                    IsuNo=expcode,
                    BnsTpCode="1",
                    OrdQty=mdposqt,
                    hname=hname,
                    sunikrt= sunikrt,
                    top_sunikrt= top_sunikrt,
                    addup_rate= addup_rate,
                    addup_cnt= addup_cnt,
                    trailing_rate= trailing_rate
                )

                send_telegram(f"🚨 {hname}은 {trailing_rate} 이하로 떨어져서 매도 신청")
            #####

            ## 애드업 비율을 넘겼으면 추가 매수 ##
            if addup_rate <= sunikrt:

                # 시장가로 누적매수량의 25%를 더 구매한다. 왜냐하면
                # 누적매수량만큼 동등한 비율로 구매하면 장의 변동으로 인해서
                # 이전까지 벌어들인 수익도 0%로 수렴할 수 있기 때문이다.
                addMd = int(mdposqt * 0.25)
                addMd = addMd if addMd > 0 else 1
                total_price = addMd * price
                addup_cnt += 1

                # 애드업하는 종목에는 전체 자산의 반만 몰아주는 것 허용
                if LS_vars.Dps < total_price:
                    continue

                # 추가구매하기
                Cspat00600_req.order(
                    accnum=os.getenv('LS-ACC'),
                    IsuNo=expcode,
                    BnsTpCode="2",
                    OrdQty=addMd,
                    hname=hname,
                    sunikrt= sunikrt,
                    top_sunikrt= top_sunikrt,
                    addup_rate=addup_rate,
                    addup_cnt= addup_cnt,
                    trailing_rate= trailing_rate
                )

                # 추가 주문후 바뀐 예수금으로 갱신 기다리기
                LS_vars.cspaq12200_renew = False
                
                send_telegram(f"🔥 {hname}은 수익률 {addup_rate} 넘겨서 추가 매수 신청")
            
            ### 텔레그램 보내주기 위해서 임시로 만든 딕셔너리 ###
            t0424_codes[expcode] = {
                "hname": hname,
                "addup_cnt": addup_cnt,
                "expcode": expcode,
                "mdposqt": mdposqt,
                "sunikrt": sunikrt,
                "top_sunikrt": top_sunikrt,
                "trailing_rate": trailing_rate,
            }
            #####
            
        ## 텔레그램에서 요청했을 경우 ##
        if LS_vars.t0424_telegram_requesting == True:
            LS_vars.t0424_telegram_requesting = False
            
            send_text = f"요청코드: {szCode}"

            for value in t0424_codes.values():
                send_text += f"""
---------
종목코드: {value["expcode"]}
종목명: {value["hname"]}
매도가능수량: {value["mdposqt"]}
최고 수익률: {value['top_sunikrt']}
현재 수익률: {value["sunikrt"]}
트렝일링 구간: {value["trailing_rate"]}
추가 매수 횟수: {value['addup_cnt']}
                """
            if len( t0424_codes.keys()) == 0:
                send_telegram(send_text + ", 비었습니다.")
            else:
                send_telegram(send_text)
        #####

        LS_vars.t0424_whileloop = False

    def calculate_sell_point(profit_rate, initial_sell=-5, step=0.7):
        """
        수익률에 따른 매도 시점을 계산하는 함수.
        
        :param profit_rate: 수익률 (%) 
        :param initial_sell: 초기 매도 시점 (%) (기본값 -5%)
        :param step: 수익률 1% 증가 시 추가되는 매도 시점 (%) (기본값 0.7%)
        :return: 계산된 매도 시점 (%)
        """
        return round(initial_sell + (profit_rate * step), 2)

    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        # 에러 났을 경우에만 실행
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            LS_vars.t0424_telegram_requesting = True
            LS_vars.t0424_whileloop = False
            print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        


class T0424_req:

    async def req():
        """
        보유종목을 요청하고
        T0424_res OnReceiveMessage 수신구간에서 증권 어플에서 주문한 종목 업데이트 / 트레일링 스탑 / 애드업을 계산하고 주문한다
        """

        if LS_vars.t0424_event is None:
            LS_vars.t0424_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", T0424_res)
            LS_vars.t0424_event.ResFileName = "C:/LS_SEC/xingAPI/Res/t0424.res"

        LS_vars.t0424_event.SetFieldData("t0424InBlock", "accno", 0, os.getenv('LS-ACC'))  # 계좌번호
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "passwd", 0, os.getenv('LS-ACC-PWD'))  # 비밀번호
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "prcgb", 0, "1")  # 단가구분
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "chegb", 0, "2")  # 체결구분
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "dangb", 0, "0")  # 단일가구분
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "charge", 0, "1")  # 제비용포함여부
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "cts_expcode", 0, "")  # CTS_종목번호, 사용하는 경우 거의 없다.
        LS_vars.t0424_event.Request(False)

        LS_vars.t0424_whileloop = True
        while LS_vars.t0424_whileloop is True:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()


    async def loop():
        while True:
            await asyncio.sleep(3.5)
            await T0424_req.req()
import asyncio
import win32com.client
from globals import LS_vars, send_telegram
from dotenv import load_dotenv
import os
import pythoncom
from .cspat00600 import Cspat00600_req
from .cspat00800 import Cspat00800_req

load_dotenv()


class T0424_res:
    def OnReceiveData(xingApi, szCode):
        """
        보유종목 조회 응답 처리
        """
        cnt = xingApi.GetBlockCount("t0424OutBlock1")
        
        for i in range(cnt):
            shcode = xingApi.GetFieldData("t0424OutBlock1", "expcode", i)
            hname = xingApi.GetFieldData("t0424OutBlock1", "hname", i)
            mdposqt = int(xingApi.GetFieldData("t0424OutBlock1", "mdposqt", i))
            avgprc = int(xingApi.GetFieldData("t0424OutBlock1", "avgprc", i))
            price = int(xingApi.GetFieldData("t0424OutBlock1", "price", i))
            
            if mdposqt > 0:  # 보유수량이 있는 경우만 처리
                # 기존 포지션 정보가 없으면 새로 생성
                if shcode not in LS_vars.stock_positions:
                    LS_vars.stock_positions[shcode] = {
                        "shcode": shcode,
                        "hname": hname,
                        "qty": mdposqt,
                        "avg_price": avgprc,
                        "current_price": price,
                        "today_low": price,  # 초기값은 현재가
                        "profit_rate": 0.0,
                        "sell_3_qty": mdposqt // 3,
                        "sell_5_qty": mdposqt // 3,
                        "sell_7_qty": mdposqt - (mdposqt // 3) * 2,
                        "sell_3_done": False,
                        "sell_5_done": False,
                        "sell_7_done": False,
                        "low_updated": False,
                        "status": "active"
                    }
                else:
                    # 기존 포지션 업데이트
                    position = LS_vars.stock_positions[shcode]
                    position["qty"] = mdposqt
                    position["current_price"] = price
                    
                    # 당일 저가 갱신 체크
                    if price < position["today_low"]:
                        position["today_low"] = price
                        position["low_updated"] = True
                        
                        # 저가 갱신 시 매도 주문 정정
                        T0424_res.update_sell_orders(position)
                    
                    # 수익률 계산
                    position["profit_rate"] = (
                        (price - avgprc) / avgprc * 100
                    )
                
                # 매도 조건 체크 및 주문
                T0424_res.check_sell_conditions(LS_vars.stock_positions[shcode])
        
        LS_vars.t0424_whileloop = False

    @staticmethod
    def check_sell_conditions(position):
        """
        매도 조건 체크 및 주문 실행
        """
        shcode = position["shcode"]
        hname = position["hname"]
        today_low = position["today_low"]
        current_price = position["current_price"]

        # 당일 저가 기준 +3%, +5%, +7% 가격 계산
        target_3_price = int(today_low * 1.03)
        target_5_price = int(today_low * 1.05)
        target_7_price = int(today_low * 1.07)

        # 3% 매도 조건
        if (not position["sell_3_done"] and
            current_price >= target_3_price and
            position["sell_3_qty"] > 0):

            Cspat00600_req.sell_order(
                shcode, position["sell_3_qty"], target_3_price,
                "3% 분할매도", hname
            )
            position["sell_3_done"] = True
            
        # 5% 매도 조건
        if (not position["sell_5_done"] and 
            current_price >= target_5_price and 
            position["sell_5_qty"] > 0):
            
            Cspat00600_req.sell_order(
                shcode, position["sell_5_qty"], target_5_price,
                "5% 분할매도", hname
            )
            position["sell_5_done"] = True
            
        # 7% 매도 조건 (전량매도)
        if (not position["sell_7_done"] and 
            current_price >= target_7_price):
            
            Cspat00600_req.sell_order(
                shcode, position["qty"], target_7_price,
                "7% 전량매도", hname
            )
            position["sell_7_done"] = True
            position["status"] = "completed"
        
        # 손절 조건: 한번이라도 매도 후 저가 갱신
        if (position["low_updated"] and 
            (position["sell_3_done"] or position["sell_5_done"]) and
            position["status"] == "active"):
            
            Cspat00600_req.sell_order(
                shcode, position["qty"], 0,  # 시장가
                "손절 전량매도", hname
            )
            position["status"] = "stop_loss"
            
            send_telegram(
                f"🚨 손절매도: {hname}\n"
                f"저가 갱신으로 인한 전량매도 실행"
            )

    @staticmethod
    def update_sell_orders(position):
        """
        저가 갱신 시 기존 매도 주문 정정
        """
        shcode = position["shcode"]
        today_low = position["today_low"]
        
        # 새로운 목표가 계산
        new_target_3 = int(today_low * 1.03)
        new_target_5 = int(today_low * 1.05)
        new_target_7 = int(today_low * 1.07)
        
        # 기존 주문 정정 (미체결 주문만)
        if not position["sell_3_done"]:
            Cspat00800_req.modify_order(shcode, new_target_3, "3%")
        if not position["sell_5_done"]:
            Cspat00800_req.modify_order(shcode, new_target_5, "5%")
        if not position["sell_7_done"]:
            Cspat00800_req.modify_order(shcode, new_target_7, "7%")
        
        send_telegram(
            f"📊 저가 갱신: {position['hname']}\n"
            f"새로운 저가: {today_low:,}원\n"
            f"매도가 정정완료"
        )

    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        if (int(systemError) == 1 or int(messageCode) < 0 or 
            (1000 <= int(messageCode) <= 9999)):
            LS_vars.t0424_whileloop = False
            print(f"T0424 오류: {systemError}, {messageCode}, {message}")


class T0424_req:
    async def req():
        """
        보유종목 조회 요청
        """
        if LS_vars.t0424_event is None:
            LS_vars.t0424_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAQuery", T0424_res
            )
            LS_vars.t0424_event.ResFileName = "C:/LS_SEC/xingAPI/Res/t0424.res"

        LS_vars.t0424_event.SetFieldData(
            "t0424InBlock", "accno", 0, os.getenv('LS-ACC')
        )
        LS_vars.t0424_event.SetFieldData(
            "t0424InBlock", "passwd", 0, os.getenv('LS-ACC-PWD')
        )
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "prcgb", 0, "1")
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "chegb", 0, "2")
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "dangb", 0, "0")
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "charge", 0, "1")
        LS_vars.t0424_event.SetFieldData("t0424InBlock", "cts_expcode", 0, "")
        LS_vars.t0424_event.Request(False)

        LS_vars.t0424_whileloop = True
        while LS_vars.t0424_whileloop:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()

    async def loop():
        """
        보유종목 조회 반복 실행 (3초마다)
        """
        while True:
            await asyncio.sleep(3)
            await T0424_req.req()

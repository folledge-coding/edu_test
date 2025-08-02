import win32com.client
from globals import LS_vars, send_telegram


class SC0_res:
    def OnReceiveRealData(xingAPI, szTrCode):
        """
        실시간 주식체결 데이터 수신
        """
        shcode = xingAPI.GetFieldData("OutBlock", "chcode")  # 종목코드
        price = int(xingAPI.GetFieldData("OutBlock", "price"))  # 현재가
        
        # 보유종목인 경우에만 처리
        if shcode in LS_vars.stock_positions:
            position = LS_vars.stock_positions[shcode]
            old_price = position["current_price"]
            position["current_price"] = price
            
            # 당일 저가 갱신 체크
            if price < position["today_low"]:
                position["today_low"] = price
                position["low_updated"] = True
                
                send_telegram(
                    f"📉 저가 갱신: {position['hname']}\n"
                    f"이전 저가: {old_price:,}원\n"
                    f"새로운 저가: {price:,}원"
                )
                
                # 저가 갱신 시 매도 주문 재설정
                from .t0424 import T0424_res
                T0424_res.update_sell_orders(position)
            
            # 수익률 업데이트
            position["profit_rate"] = (
                (price - position["avg_price"]) / position["avg_price"] * 100
            )
            
            # 매도 조건 체크
            from .t0424 import T0424_res
            T0424_res.check_sell_conditions(position)


class SC0_req:
    @staticmethod
    def subscribe_stocks():
        """
        보유종목들의 실시간 시세 구독
        """
        if LS_vars.sc0_event is None:
            LS_vars.sc0_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAReal", SC0_res
            )
            LS_vars.sc0_event.ResFileName = "C:/LS_SEC/xingAPI/Res/SC0.res"
        
        # 보유종목들 구독
        for shcode in LS_vars.stock_positions.keys():
            LS_vars.sc0_event.SetFieldData("InBlock", "shcode", shcode)
            LS_vars.sc0_event.AdviseRealData()
            
        send_telegram(
            f"📡 실시간 시세 구독 완료\n"
            f"구독 종목 수: {len(LS_vars.stock_positions)}개"
        )

import win32com.client
from globals import LS_vars, send_telegram


class SC1_res:
    def OnReceiveRealData(xingAPI, szTrCode):
        """
        실시간 주문체결 데이터 수신
        """
        ordxctptncode = xingAPI.GetFieldData("OutBlock", "ordxctptncode")
        accno = xingAPI.GetFieldData("OutBlock", "accno1")
        isunm = xingAPI.GetFieldData("OutBlock", "Isunm")
        execqty = int(xingAPI.GetFieldData("OutBlock", "execqty"))
        execprc = int(xingAPI.GetFieldData("OutBlock", "execprc"))
        shtnIsuno = xingAPI.GetFieldData("OutBlock", "shtnIsuno")
        bnstp = xingAPI.GetFieldData("OutBlock", "bnstp")
        
        # 단축코드를 전체코드로 변환
        shcode = SC1_res.convert_to_full_code(shtnIsuno)
        
        # 체결 완료이고 매도인 경우
        if ordxctptncode == "11" and bnstp == "1":
            send_telegram(
                f"✅ 매도체결 완료\n"
                f"계좌: {accno}\n"
                f"종목: {isunm} ({shcode})\n"
                f"체결가: {execprc:,}원\n"
                f"체결량: {execqty:,}주"
            )
            
            # 보유종목 정보 업데이트
            if shcode in LS_vars.stock_positions:
                position = LS_vars.stock_positions[shcode]
                position["qty"] -= execqty
                
                # 전량 매도된 경우 포지션 삭제
                if position["qty"] <= 0:
                    del LS_vars.stock_positions[shcode]
                    send_telegram(f"🏁 {isunm} 전량매도 완료")

    @staticmethod
    def convert_to_full_code(short_code):
        """
        단축 종목코드를 6자리 종목코드로 변환
        예: "A005930" -> "005930"
        """
        if len(short_code) != 7 or not short_code[0].isalpha():
            return short_code
        return short_code[1:]


class SC1_req:
    @staticmethod
    def subscribe():
        """
        실시간 주문체결 데이터 구독
        """
        if LS_vars.sc1_event is None:
            LS_vars.sc1_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAReal", SC1_res
            )
            LS_vars.sc1_event.ResFileName = "C:/LS_SEC/xingAPI/Res/SC1.res"
            LS_vars.sc1_event.AdviseRealData()
            
        send_telegram("📡 실시간 주문체결 구독 완료")

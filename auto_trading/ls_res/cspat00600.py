import win32com.client
from globals import LS_vars, send_telegram
from dotenv import load_dotenv
import os

load_dotenv()


class Cspat00600_res:
    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        주문 결과 메시지 처리
        """
        if (int(systemError) == 1 or int(messageCode) < 0 or
                (1000 <= int(messageCode) <= 9999)):
            print(f"주문 오류: {systemError}, {messageCode}, {message}")
            send_telegram(f"❌ 주문 실패: {message}")
        else:
            print(f"주문 성공: {message}")


class Cspat00600_req:
    @staticmethod
    def sell_order(shcode, qty, price, order_type, hname):
        """
        매도 주문 실행
        
        Args:
            shcode: 종목코드
            qty: 주문수량
            price: 주문가격 (0이면 시장가)
            order_type: 주문타입 (3%, 5%, 7%, 손절)
            hname: 종목명
        """
        if LS_vars.cspat00600_event is None:
            LS_vars.cspat00600_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAQuery", Cspat00600_res
            )
            LS_vars.cspat00600_event.ResFileName = (
                "C:/LS_SEC/xingAPI/Res/CSPAT00600.res"
            )

        # 주문가격 타입 설정 (0: 시장가, 그외: 지정가)
        ord_prc_tp = "03" if price == 0 else "00"
        
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "AcntNo", 0, os.getenv('LS-ACC')
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "InptPwd", 0, os.getenv('LS-ACC-PWD')
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "IsuNo", 0, shcode
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "OrdQty", 0, qty
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "OrdPrc", 0, price
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "BnsTpCode", 0, "1"  # 매도
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "OrdprcPtnCode", 0, ord_prc_tp
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "MgntrnCode", 0, "000"
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "LoanDt", 0, ""
        )
        LS_vars.cspat00600_event.SetFieldData(
            "CSPAT00600InBlock1", "OrdCndiTpCode", 0, "0"
        )
        
        LS_vars.cspat00600_event.Request(False)
        
        # 텔레그램 알림
        price_text = "시장가" if price == 0 else f"{price:,}원"
        send_telegram(
            f"📤 {order_type} 매도주문\n"
            f"종목: {hname} ({shcode})\n"
            f"수량: {qty:,}주\n"
            f"가격: {price_text}"
        )

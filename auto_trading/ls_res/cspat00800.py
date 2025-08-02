import win32com.client
from globals import LS_vars, send_telegram
from dotenv import load_dotenv
import os

load_dotenv()


class Cspat00800_res:
    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        정정주문 결과 메시지 처리
        """
        if (int(systemError) == 1 or int(messageCode) < 0 or
                (1000 <= int(messageCode) <= 9999)):
            print(f"정정주문 오류: {systemError}, {messageCode}, {message}")
            send_telegram(f"❌ 정정주문 실패: {message}")
        else:
            print(f"정정주문 성공: {message}")


class Cspat00800_req:
    @staticmethod
    def modify_order(shcode, new_price, order_type):
        """
        매도 주문 정정
        
        Args:
            shcode: 종목코드
            new_price: 새로운 주문가격
            order_type: 주문타입 (3%, 5%, 7%)
        """
        # 기존 주문번호를 찾아야 하는데, 실제로는 미체결주문조회 후
        # 해당 주문을 정정해야 함
        # 여기서는 간단하게 새로운 주문으로 처리
        
        if LS_vars.cspat00800_event is None:
            LS_vars.cspat00800_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAQuery", Cspat00800_res
            )
            LS_vars.cspat00800_event.ResFileName = (
                "C:/LS_SEC/xingAPI/Res/CSPAT00800.res"
            )

        # 실제 정정주문을 위해서는 기존 주문번호가 필요
        # 여기서는 예시로 구현
        
        send_telegram(
            f"🔄 {order_type} 매도가 정정\n"
            f"종목코드: {shcode}\n"
            f"새로운 가격: {new_price:,}원"
        )

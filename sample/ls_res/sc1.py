from dotenv import load_dotenv
import os
import win32com.client
from globals import LS_vars, send_telegram
from database.method_db import getPassedStock, insertPassedStock, deletePassedStock, updatePassedOnlyStatus, updatePassedToInfo
from database.account_db import deleteTempOrderingStock, getTempOrderingStock

class SC1_res:
    def OnReceiveRealData(xingAPI, szTrCode):
        ordxctptncode = xingAPI.GetFieldData("OutBlock", "ordxctptncode")  # 체결구분: 11
        accno1 = xingAPI.GetFieldData("OutBlock", "accno1")  # 계좌번호
        Isunm = xingAPI.GetFieldData("OutBlock", "Isunm")  # 종목명
        execqty = xingAPI.GetFieldData("OutBlock", "execqty")  # 체결수량
        execprc = xingAPI.GetFieldData("OutBlock", "execprc")  # 체결가격
        shtnIsuno = xingAPI.GetFieldData("OutBlock", "shtnIsuno")  # 단축종목번호
        shcode = SC1_res.convert_to_full_code(shtnIsuno)
        bnstp = xingAPI.GetFieldData("OutBlock", "bnstp")  # 매매구분

        orderingStock = getTempOrderingStock(shcode)
        addup_rate = orderingStock.get("addup_rate", 30.0)
        addup_cnt = orderingStock.get("addup_cnt", 0)
        trailing_rate = orderingStock.get("trailing_rate", -5.0)
        top_sunikrt = orderingStock.get("top_sunikrt", 0.0)
        
        # 프로그램을 통해서가 아니라, 증권사의 어플로 주문했을 경우에는 처음 수신하는 종목일 확률이 있으니깐
        # method로부터 추출된 종목 리스트에 포함되어 있는지 확인한다.
        passedStock = getPassedStock(shcode)
        status = passedStock.get("status", None)
        
        # 매수/매도 사이클 완료 and "11"체결 and "매수"
        if status == "complete" and ordxctptncode == "11" and bnstp == "2":
            # 주문 체결이 되었는데, 이미 매도까지 했던 종목이라면, 증권 어플에서 따로 주문 넣었을 확률이 있다.
            # 그럴때는 주시하는 종목을 초기화해서 다시 저장해야 하니깐 종목을 테이블에서 지워준다.
            deletePassedStock(shcode)
            status = None
        
        # 종목이 존재 안 하면 주시하기 위해서 추가한다.
        if status is None:
            insertPassedStock({
                "method_id":"app",
                "shcode": shcode,
                "status": "no"
            })


        # 체결이 완료되었으니깐, 임시 저장소에서 지운다.
        deleteTempOrderingStock(
            shcode=shcode
        )

        # "11"체결 and 매도
        if ordxctptncode == "11" and bnstp == "1":

            # 매도 완료했음으로 상태 업데이트한다.
            updatePassedOnlyStatus(
                shcode=shcode,
                status="complete"
            )

            send_telegram(f"""
전량매도
계좌번호: {accno1}
종목명: {Isunm}
종목코드: {shcode}
체결가격: {execprc}
체결수량: {execqty}
""")

        # 체결, 매수
        elif ordxctptncode == "11" and bnstp == "2":

            # addup 횟수만큼 다음 애드업 구간도 높인다
            addup_rate = 30 + 15*addup_cnt

            updatePassedToInfo(
                shcode=shcode,
                addup_rate=addup_rate,
                addup_cnt=addup_cnt,
                top_sunikrt=top_sunikrt,
                trailing_rate=trailing_rate,
                status="account"
            )
            

            send_telegram(f"""
매수체결
계좌번호: {accno1}
종목명: {Isunm}
종목코드: {shcode}
체결가격: {execprc}
체결수량: {execqty}
""")


    def convert_to_full_code(short_code):
        """
        LS증권 xingAPI에서 사용하는 단축 종목코드를 6자리 종목코드로 변환하는 함수입니다.
        예를 들어, "A005930" -> "005930"으로 변환합니다.
        
        :param short_code: 단축 종목코드 (예: "A005930")
        :return: 6자리 종목코드 (예: "005930")
        :raises ValueError: 단축 종목코드 형식이 올바르지 않을 경우 발생
        """
        # 단축코드는 첫 번째 글자가 알파벳이고, 총 길이가 7자리여야 합니다.
        if len(short_code) != 7 or not short_code[0].isalpha():
            raise ValueError(f"잘못된 단축 종목코드입니다: {short_code}")
        
        # 앞의 한 글자를 제거하여 6자리 종목코드를 반환합니다.
        return short_code[1:]


class SC1_req:
    def req():
        """
        실시간 주문체결 데이터 요청
        """
        
        if LS_vars.sc1_event is None:
            LS_vars.sc1_event = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", SC1_res)
            LS_vars.sc1_event.ResFileName = "C:/LS_SEC/xingAPI/Res/SC1.res"
            LS_vars.sc1_event.AdviseRealData()


import asyncio
import win32com
from globals import LS_vars, send_telegram
import decimal
from datetime import datetime, timedelta
import pythoncom

class G3204_res:
    def OnReceiveData(xingApi, szCode):
        nDecompSize = xingApi.Decompress("g3204OutBlock1")
        if nDecompSize == 0:
            LS_vars.g3204_whileloop = True
            return
        
        cnt = xingApi.GetBlockCount("g3204OutBlock1")
        prevDate = xingApi.GetFieldData("g3204OutBlock1", "date", 0)
        prevPrice = decimal.Decimal(xingApi.GetFieldData("g3204OutBlock1", "close", 0))
        curDate = xingApi.GetFieldData("g3204OutBlock1", "date", cnt-1)
        curPrice = decimal.Decimal(xingApi.GetFieldData("g3204OutBlock1", "close", cnt-1))
        
        drate = (curPrice - prevPrice) / prevPrice * 100
        drate = round(drate)
        
        if drate >= LS_vars.america_drate:
            print(f"미국증시 통과, 등락율차이:{drate}")
            LS_vars.america_drate_pass = True

        LS_vars.g3204_whileloop = True

    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        # 에러 났을 경우에만 실행
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            LS_vars.g3204_whileloop = True
            print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        

class G3204_req:
    
    async def req(days=365):
        """
        미국증시 요청하기
        """
        
        # 현재 날짜 및 시간 가져오기
        current_date = datetime.now()

        # 현재 날짜를 yyyymmdd 형식으로 변환
        endDateStr = current_date.strftime('%Y%m%d')

        ### 미국증시 1년치로 계산 ###
        startDate = current_date - timedelta(days=days)
        startDateStr = startDate.strftime('%Y%m%d')

        if LS_vars.g3204_event is None:
            LS_vars.g3204_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", G3204_res)
            LS_vars.g3204_event.ResFileName = "C:/LS_SEC/xingAPI/Res/g3204.res"

        LS_vars.g3204_event.SetFieldData("g3204InBlock", "delaygb", 0, "R")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "keysymbol", 0, "82NDAQ")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "exchcd", 0, "82")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "symbol", 0, "NDAQ")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "gubun", 0, "2")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "qrycnt", 0, 2000)
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "comp_yn", 0, "Y")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "sdate", 0, startDateStr)
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "edate", 0, endDateStr) 
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "cts_date", 0, "")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "cts_info", 0, "")
        LS_vars.g3204_event.SetFieldData("g3204InBlock", "sujung", 0, "N")
        LS_vars.g3204_event.Request(False)
        
        LS_vars.g3204_whileloop = False
        while LS_vars.g3204_whileloop == False:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()

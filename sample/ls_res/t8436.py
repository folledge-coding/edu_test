import asyncio
import win32com.client
from globals import LS_vars
from dotenv import load_dotenv
import pythoncom

load_dotenv()

class T8436_res:

    def OnReceiveData(xingApi, szCode):
        cnt = xingApi.GetBlockCount("t8436OutBlock")
        for i in range(cnt):
            shcode = xingApi.GetFieldData("t8436OutBlock", "shcode", i)
            hname = xingApi.GetFieldData("t8436OutBlock", "hname", i)
            
            etfgubun = xingApi.GetFieldData("t8436OutBlock", "etfgubun", i)
            if etfgubun != "0":
                continue

            gubun = xingApi.GetFieldData("t8436OutBlock", "gubun", i)
            gubun = gubun = "kospi" if gubun == "1" else "kosdaq"

            LS_vars.t8436_scodes.append({
                "shcode": shcode,
                "hname": hname,
                "market": gubun
            })

        LS_vars.t8436_whileloop = False

    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            LS_vars.t8436_whileloop = False
            print("t8436: systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        

class T8436_req:

    async def req():
        """
        코스피 / 코스닥 종목들 수신 요청
        """
        
        if LS_vars.t8436_event is None:
            LS_vars.t8436_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", T8436_res)
            LS_vars.t8436_event.ResFileName = "C:/LS_SEC/xingAPI/Res/t8436.res"

        LS_vars.t8436_event.SetFieldData("t8436InBlock", "gubun", 0, "0")
        LS_vars.t8436_event.Request(False)
        
        LS_vars.t8436_scodes.clear() # 종목 다시 담게 비워줌
        LS_vars.t8436_whileloop = True
        while LS_vars.t8436_whileloop == True:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()
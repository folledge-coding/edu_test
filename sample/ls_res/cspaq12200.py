import asyncio
from dotenv import load_dotenv
import os
import win32com.client
from globals import LS_vars, send_telegram
import locale
import pythoncom

load_dotenv()
locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')  # 한국의 원화 단위로 표시하기 위해서 현재 지역을 설정한다.

class Cspaq1220_res:

    def OnReceiveData(xingAPI, szCode):
        AcntNo = xingAPI.GetFieldData("CSPAQ12200OutBlock1", "AcntNo", 0)  # 계좌번호
        Dps = int(xingAPI.GetFieldData("CSPAQ12200OutBlock2", "Dps", 0))  # 예수금

        LS_vars.Dps = Dps
        LS_vars.cspaq12200_renew = True
        LS_vars.cspaq12200_whileloop = False

        if LS_vars.cspaq12200_telegram_requesting == True:
            LS_vars.cspaq12200_telegram_requesting = False
            send_telegram(f"""
요청코드: {szCode}
계좌번호: {AcntNo}
예수금: {locale.currency(Dps, grouping=True)}
                """)
    
    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        # 에러 났을 경우에만 실행
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            LS_vars.cspaq12200_telegram_requesting= False
            LS_vars.cspaq12200_renew = True # 예수금 갱신이 안 되도 일단 완료로 바꾸기
            LS_vars.cspaq12200_whileloop = False
            print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        


class Cspaq1220_req:
    async def req():
        """
        예수금 요청하기
        """
        
        if LS_vars.cspaq12200_event is None:
            LS_vars.cspaq12200_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", Cspaq1220_res)
            LS_vars.cspaq12200_event.ResFileName = "C:/LS_SEC/xingAPI/Res/CSPAQ12200.res"

        LS_vars.cspaq12200_event.SetFieldData("CSPAQ12200InBlock1", "RecCnt", 0, 1)
        LS_vars.cspaq12200_event.SetFieldData("CSPAQ12200InBlock1", "MgmtBrnNo", 0, "")
        LS_vars.cspaq12200_event.SetFieldData("CSPAQ12200InBlock1", "AcntNo", 0, os.getenv('LS-ACC'))
        LS_vars.cspaq12200_event.SetFieldData("CSPAQ12200InBlock1", "Pwd", 0, os.getenv('LS-ACC-PWD'))
        LS_vars.cspaq12200_event.SetFieldData("CSPAQ12200InBlock1", "BalCreTp", 0, "0")
        LS_vars.cspaq12200_event.Request(False)

        LS_vars.cspaq12200_whileloop = True
        while LS_vars.cspaq12200_whileloop is True:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()

        
    async def loop():
        while True:
            await asyncio.sleep(6)
            await Cspaq1220_req.req()

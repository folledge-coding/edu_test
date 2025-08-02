import asyncio
import win32com.client
from globals import LS_vars, send_telegram
from dotenv import load_dotenv
import os
import pythoncom

load_dotenv()


class Cspaq12200_res:
    def OnReceiveData(xingAPI, szCode):
        """
        예수금 조회 응답 처리
        """
        acnt_no = xingAPI.GetFieldData("CSPAQ12200OutBlock1", "AcntNo", 0)
        dps = int(xingAPI.GetFieldData("CSPAQ12200OutBlock2", "Dps", 0))
        
        LS_vars.Dps = dps
        LS_vars.cspaq12200_whileloop = False
        
        send_telegram(
            f"💰 예수금 조회\n"
            f"계좌: {acnt_no}\n"
            f"예수금: {dps:,}원"
        )

    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        if (int(systemError) == 1 or int(messageCode) < 0 or
                (1000 <= int(messageCode) <= 9999)):
            LS_vars.cspaq12200_whileloop = False
            print(f"예수금 조회 오류: {systemError}, {messageCode}, {message}")


class Cspaq12200_req:
    async def req():
        """
        예수금 조회 요청
        """
        if LS_vars.cspaq12200_event is None:
            LS_vars.cspaq12200_event = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAQuery", Cspaq12200_res
            )
            LS_vars.cspaq12200_event.ResFileName = (
                "C:/LS_SEC/xingAPI/Res/CSPAQ12200.res"
            )

        LS_vars.cspaq12200_event.SetFieldData(
            "CSPAQ12200InBlock1", "RecCnt", 0, 1
        )
        LS_vars.cspaq12200_event.SetFieldData(
            "CSPAQ12200InBlock1", "MgmtBrnNo", 0, ""
        )
        LS_vars.cspaq12200_event.SetFieldData(
            "CSPAQ12200InBlock1", "AcntNo", 0, os.getenv('LS-ACC')
        )
        LS_vars.cspaq12200_event.SetFieldData(
            "CSPAQ12200InBlock1", "Pwd", 0, os.getenv('LS-ACC-PWD')
        )
        LS_vars.cspaq12200_event.SetFieldData(
            "CSPAQ12200InBlock1", "BalCreTp", 0, "0"
        )
        LS_vars.cspaq12200_event.Request(False)

        LS_vars.cspaq12200_whileloop = True
        while LS_vars.cspaq12200_whileloop:
            await asyncio.sleep(0.01)
            pythoncom.PumpWaitingMessages()

    async def loop():
        """
        예수금 조회 반복 실행 (5분마다)
        """
        while True:
            await asyncio.sleep(300)  # 5분
            await Cspaq12200_req.req()

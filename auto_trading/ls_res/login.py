from dotenv import load_dotenv
import os
import win32com.client
from globals import send_telegram
import pythoncom

load_dotenv()


class Login_res:
    login_ok = False

    def OnLogin(self, szCode, szMsg):
        if szCode == "0000":
            send_telegram("✅ LS증권 자동매매 시스템 로그인 완료")
            Login_res.login_ok = True
        else:
            send_telegram(f"❌ 로그인 실패: {szMsg}")
            Login_res.login_ok = False


class Login_req:
    def req(self):
        """
        XingAPI 로그인 요청
        """
        session = win32com.client.DispatchWithEvents(
            "XA_Session.XASession", Login_res
        )
        session.ConnectServer(os.getenv('LS-URL'), 20001)
        session.Login(
            os.getenv('LS-ID'),
            os.getenv('LS-PASSWORD'),
            os.getenv('LS-CERT'),
            0,
            False
        )

        while Login_res.login_ok is False:
            pythoncom.PumpWaitingMessages()

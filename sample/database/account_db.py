from datetime import datetime
from globals import  AccDict, cursor, conn

def createAccountsTable():
    """
    계좌번호 테이블 생성

    :param accnum: 계좌번호
    :param name: 계좌명
    :param detail: 계좌설명
    """
    
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   accnum TEXT UNIQUE NOT NULL, 
                   name TEXT, 
                   detail TEXT
                   )''')
    conn.commit()
    
def insertAccounts(accounts:list[AccDict]):
    """
    계좌 테이블을 생성하고 세팅된 계좌를 추가하는 함수
    """

    data = [(account['accnum'], account["name"], account["detail"]) for account in accounts]  # 1만 개 데이터

    cursor.execute("BEGIN TRANSACTION")

    cursor.executemany("""
                       INSERT INTO accounts (accnum, name, detail)
                       VALUES (?, ?, ?)
                       ON CONFLICT(accnum) DO NOTHING
                       """, data)

    conn.commit()

def insertTempOrderingStock(
    expcode: str,
    hname: str, # 종목명
    mdposqt: int, # 매도가능수량
    sunikrt: float,  # 수익율
    top_sunikrt: float, # 최고 수익률
    addup_rate:float,
    addup_cnt: int, # 애드업 갯수
    trailing_rate: float # 트레일링 구간
    ):
    cursor.execute("""
        INSERT INTO tempOrderingStocks 
            (shcode, hname, mdposqt, sunikrt, top_sunikrt,
                   addup_rate, addup_cnt, trailing_rate, create_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        expcode, 
        hname, 
        mdposqt, 
        sunikrt, 
        top_sunikrt, 
        addup_rate, 
        addup_cnt, 
        trailing_rate, 
        datetime.now().strftime("%Y-%m-%d")
    ))
        
    conn.commit()
    
def createTempOrderingStocksTable():
    """
    주문중인 종목이 중복 주문이 안 들어가도록 임시로 만든 테이블이다.
    """

    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tempOrderingStocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shcode TEXT UNIQUE NOT NULL,
                    hname TEXT NOT NULL,
                    mdposqt INTEGER DEFAULT 0,
                    sunikrt REAL DEFAULT 0,
                    top_sunikrt REAL DEFAULT 0.0,
                    addup_rate REAL DEFAULT 30.0,
                    addup_cnt INTEGER DEFAULT 0,
                    trailing_rate REAL DEFAULT -5.0,
                    create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                    FOREIGN KEY (shcode) REFERENCES passedStocks (shcode)
                )''')
    conn.commit()

def getTempOrderingStock(shcode:str):
    """
    테이블에 종목이 존재한다면 이전 주문이 완료되지 않은 것이다.
    """
    
    query = """
        SELECT *
        FROM tempOrderingStocks
        WHERE shcode = ?
    """

    cursor.execute(query, (shcode,))
    row = cursor.fetchone()

    if row:
        row_dict = dict(row)
        return row_dict
    else:
        return dict()
        

def deleteTempOrderingStock(shcode:str):
    """
    주문 처리가 모두 완료되고 임시 테이블에 종목을 지워준다
    """

    cursor.execute("""
    DELETE FROM tempOrderingStocks
    WHERE shcode = ?;
    """, (shcode,))

    conn.commit()
      

def clearTempOrderingStocks():
    """
    테이블을 비운다.
    장 중에 주문 넣은 종목이 체결까지 이뤄지지 않았다면 장 종료 후에 자동으로 증권사에서 제거한다.
    그러므로 장 종료 후 또는 장 시작전에 해당 테이블도 깨끗히 비워둔다.
    """

    cursor.execute("""
    DELETE FROM tempOrderingStocks;
    """)

    conn.commit()

        
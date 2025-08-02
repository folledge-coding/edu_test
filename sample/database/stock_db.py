from globals import T8436Dict, cursor, conn

def createStocksTable():
    """
    주식 종목 테이블 생성

    :param shcode: 종목코드
    :param hname: 종목명
    :param market: kospi | kosdaq
    """

    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute('''CREATE TABLE IF NOT EXISTS stocks (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   shcode TEXT UNIQUE NOT NULL, 
                   hname TEXT, 
                   market TEXT
                   )''')
    conn.commit()


def insertStocks(stocks:list[T8436Dict]):
    """
    주식 종목 넣기
    """

    if len(stocks) == 0:
        return

    data = [(stock['shcode'], stock["hname"], stock["market"]) for stock in stocks]  # 1만 개 데이터

    cursor.executemany("""
                       INSERT INTO stocks (shcode, hname, market)
                       VALUES (?, ?, ?)
                       ON CONFLICT(shcode) DO NOTHING
                       """, data)

    conn.commit()

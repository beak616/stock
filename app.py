from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import os

app = Flask(__name__)

def safe_round(value):
    if pd.isna(value):
        return "-"
    return round(float(value), 2)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []

    if request.method == "POST":
        symbols_input = request.form.get("symbols", "")
        symbols = symbols_input.replace(",", " ").split()

        for symbol in symbols:
            try:
                data = yf.download(symbol, period="90d", auto_adjust=True)

                if data.empty or len(data) < 25:
                    results.append({
                        "symbol": symbol,
                        "error": "資料不足"
                    })
                    continue

                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                # 現在股價
                current_price = safe_round(close.iloc[-1])

                # 計算均線
                ma5 = close.rolling(5).mean()
                ma20 = close.rolling(20).mean()

                today_ma5 = ma5.iloc[-1]
                yesterday_ma5 = ma5.iloc[-2]
                today_ma20 = ma20.iloc[-1]
                yesterday_ma20 = ma20.iloc[-2]

                # 如果有 NaN 就不判斷
                if any(pd.isna(x) for x in [today_ma5, yesterday_ma5, today_ma20, yesterday_ma20]):
                    signal = "-"
                else:
                    # 標準黃金交叉 / 死亡交叉
                    if yesterday_ma5 <= yesterday_ma20 and today_ma5 > today_ma20:
                        signal = "buy"
                    elif yesterday_ma5 >= yesterday_ma20 and today_ma5 < today_ma20:
                        signal = "sell"
                    else:
                        signal = "-"

                # 七天內交叉警示
                alert = "-"
                for i in range(1, 7):
                    if (ma5.iloc[-i] > ma20.iloc[-i] and
                        ma5.iloc[-i-1] <= ma20.iloc[-i-1]) or \
                       (ma5.iloc[-i] < ma20.iloc[-i] and
                        ma5.iloc[-i-1] >= ma20.iloc[-i-1]):
                        alert = "intersect"
                        break

                results.append({
                    "symbol": symbol.upper(),
                    "price": current_price,
                    "today_ma5": safe_round(today_ma5),
                    "yesterday_ma5": safe_round(yesterday_ma5),
                    "today_ma20": safe_round(today_ma20),
                    "yesterday_ma20": safe_round(yesterday_ma20),
                    "signal": signal,
                    "alert": alert,
                    "error": "-"
                })

            except Exception as e:
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })

    return render_template("ind.html", results=results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import json
import os

app = Flask(__name__)

stock_map = {}
reverse_map = {}

def initialize_stock_data():
    global stock_map, reverse_map
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "stocks.json")
        
        with open(json_path, "r", encoding="utf-8") as f:
            data_json = json.load(f)
            
        df = pd.DataFrame(data_json)
        
        stock_map = dict(zip(df["Name"], df["Code"].astype(str) + ".TW"))
        for name, code in stock_map.items():
            reverse_map[code] = name
            reverse_map[code.replace(".TW", "")] = name
        print("✅ 本地 JSON 股票資料載入成功！")
    except Exception as e:
        print(f"❌ 本地 JSON 載入失敗，原因: {e}")
        stock_map = {}
        reverse_map = {}

initialize_stock_data()

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
                symbol = symbol.strip()

                if symbol in stock_map:
                    symbol = stock_map[symbol]
                elif symbol.isdigit():
                    symbol = symbol + ".TW"
                
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

                current_price = safe_round(close.iloc[-1])

                ma5 = close.rolling(5).mean()
                ma20 = close.rolling(20).mean()

                today_ma5 = ma5.iloc[-1]
                yesterday_ma5 = ma5.iloc[-2]
                today_ma20 = ma20.iloc[-1]
                yesterday_ma20 = ma20.iloc[-2]

                if any(pd.isna(x) for x in [today_ma5, yesterday_ma5, today_ma20, yesterday_ma20]):
                    signal = "-"
                else:
                    if yesterday_ma5 <= yesterday_ma20 and today_ma5 > today_ma20:
                        signal = "buy"
                    elif yesterday_ma5 >= yesterday_ma20 and today_ma5 < today_ma20:
                        signal = "sell"
                    else:
                        signal = "-"

                alert = "-"
                for i in range(1, 7):
                    if (ma5.iloc[-i] > ma20.iloc[-i] and
                        ma5.iloc[-i-1] <= ma20.iloc[-i-1]) or \
                       (ma5.iloc[-i] < ma20.iloc[-i] and
                        ma5.iloc[-i-1] >= ma20.iloc[-i-1]):
                        alert = "intersect"
                        break
                        
                code = symbol.replace(".TW", "")
                display_name = reverse_map.get(code, code)
                results.append({
                    "symbol": f"{display_name} ({code})",
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

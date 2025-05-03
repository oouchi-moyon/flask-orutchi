from flask import Flask, render_template_string
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

@app.route('/')
def show_averages():
    # CSVのURL
    url = "https://kaken.odaiba.online/oouchi/data/classdat_set_test_test.csv"

    # CSVを読み込む（1行目をデータとして読み込むため、header=None）
    df = pd.read_csv(url, header=None)

    # 必要な列（U〜AK）を取り出すために列番号で指定
    target_columns = df.iloc[:, 20:37]

    # 各列の平均値を計算
    averages = target_columns.mean()

    # グラフを作成
    fig, ax = plt.subplots()
    ax.bar(range(len(averages)), averages, color='skyblue')

    # 横軸の列番号を設定
    ax.set_xticks(range(len(averages)))  # 各バーの位置に対応するx軸の目盛りを設定
    ax.set_xticklabels(range(21, 38))  # U列は21番目、AK列は37番目なので、それに対応する番号を設定

    # グラフの設定
    ax.set_xlabel('列番号')
    ax.set_ylabel('平均値')
    ax.set_title('U列〜AK列の平均値')
    ax.set_ylim(0, 1)  # 縦軸を0〜1に設定

    # グラフを画像として保存し、Base64でエンコードしてHTMLに埋め込む
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

    # 各列の平均値を文字で表示
    averages_list = "<ul>"
    for i, avg in enumerate(averages):
        averages_list += f"<li>列 {i + 21}: {avg:.2f}</li>"  # 列番号21から始めて表示
    averages_list += "</ul>"

    # HTMLに埋め込む
    html = f"""
    <h2>U列〜AK列の平均値（グラフ表示）</h2>
    <img src="data:image/png;base64,{img_base64}" />
    <h3>各列の平均値</h3>
    {averages_list}
    """

    return render_template_string(html)

if __name__ == '__main__':
    app.run(debug=True)
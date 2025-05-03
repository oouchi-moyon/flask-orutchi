from flask import Flask, render_template
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

@app.route('/')
def show_averages():
    # CSV ファイルの読み込み
    df = pd.read_csv('https://kaken.odaiba.online/oouchi/data/classdat_set_test_test.csv')

    # U列からAK列の平均値を計算
    target_columns = df.iloc[:, 20:37]  # 21番目から37番目の列
    column_means = target_columns.mean()

    # グラフの作成
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(column_means.index, column_means.values)
    ax.set_xlabel('Column')
    ax.set_ylabel('Average Value')
    ax.set_title('Average Value for Columns U to AK')

    # グラフを画像として保存し、HTMLで表示できるようにエンコード
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
    img.close()

    return render_template('index.html', column_means=column_means, img_data=img_b64)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # RenderがPORTを指定してくる
    app.run(host='0.0.0.0', port=port)

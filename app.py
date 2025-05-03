from flask import Flask, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import matplotlib

# 日本語フォント設定
matplotlib.rcParams['font.family'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'Arial']

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def show_averages():
    # データ読み込み
    df = pd.read_csv('https://kaken.odaiba.online/oouchi/data/classdat_set_test_test.csv')

    filter_value = ''
    filtered_df = df
    no_data_found = False

    if request.method == 'POST':
        filter_value = request.form.get('filter_value', '')
        if filter_value.strip() != '':
            filtered_df = df[df.iloc[:, 3].astype(str) == filter_value]
            if filtered_df.empty:
                no_data_found = True

    # 対象列：21列目〜37列目（インデックス20〜36）
    target_column_names = df.columns[20:37]

    # 日本語ラベル
    japanese_labels = [
        "児童：教師と授業内容に関係した相互交渉をする",
        "児童：教師と授業内容とは関係のない相互交渉をする",
        "児童：教師や他児の話を聞く",
        "児童：教室全体に影響する程度に授業を妨げる",
        "児童：他児と授業内容に関係した相互交渉をする",
        "児童：他児と授業内容に関係しない相互交渉をする",
        "児童：一人で他者の話を聞く以外の学習活動を行う",
        "児童：対象児が一人で学習活動以外の行動をとる",
        "児童：判定不能",
        "教師：児童の不適切な行動や授業規律の維持への対応をする",
        "教師：授業内容の説明や例示をする",
        "教師：児童との授業内容に関連した相互交渉をする",
        "教師：児童がとるべき行動の指示をする",
        "教師：説明をともなわない板書をする",
        "教師：机間巡視，机間指導，グループに対する指導をする",
        "教師：学習活動の準備をする",
        "教師：判定不能"
    ]

    # 平均値計算または初期化
    if filter_value.strip() == '' or filtered_df.empty:
        column_means = pd.Series([0.0] * len(japanese_labels), index=japanese_labels)
    else:
        target_columns = filtered_df.iloc[:, 20:37]
        column_means = target_columns.mean()
        column_means.index = japanese_labels

    # グラフ生成（ここから下を関数内に入れる）
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.bar(column_means.index.astype(str), column_means.values)
    ax.set_xticklabels(column_means.index, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_xlabel('行動カテゴリ')
    ax.set_ylabel('平均値')
    ax.set_title('平均値の棒グラフ')
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
    img.close()

    return render_template(
        'index.html',
        column_means=column_means,
        img_data=img_b64,
        no_data_found=no_data_found
    )

if __name__ == "__main__":
    app.run(debug=True)

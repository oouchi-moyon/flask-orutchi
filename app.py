from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
import requests
from io import BytesIO, StringIO
import chardet
import tempfile
import os
import base64

app = Flask(__name__)

app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS前提の環境（Renderなど）

app.secret_key = 'your_secret_key'

BASE_URL = "http://orutchi.educpsychol.com/data/"
observation_table_global = None
detail_data_global = []

def read_csv_with_encoding_auto(response_content):
    result = chardet.detect(response_content)
    encoding = result['encoding']
    return pd.read_csv(StringIO(response_content.decode(encoding)), header=None)


def create_display_grid(df):
    grid = []
    total_cols = df.shape[1]
    empty_list = []
    absent_list = []
    no_obs_list = []

    for i in range(7):
        row = []
        for j in range(7):
            num = i * 7 + j + 1
            if num > 49:
                row.append({"text": "", "style": ""})
                continue
            col_index = num + 10 
            
            if col_index >= total_cols:
                row.append({"text": "", "style": ""})
                continue
            values = df.iloc[:, col_index].dropna().astype(str).map(lambda x: x.strip())
            if all(v == "N" for v in values):
                empty_list.append(str(num))
                row.append({"text": "空", "style": ""})
            elif all(v == "A" for v in values):
                absent_list.append(str(num))
                row.append({"text": "欠", "style": ""})
            elif all(v == "0" for v in values):
                no_obs_list.append(str(num))
                row.append({"text": str(num), "style": "color:red;"})
            else:
                if num == 49:
                    row.append({"text": "教師", "style": ""})
                else:
                    row.append({"text": str(num), "style": ""})
        grid.append(row)

    return grid, empty_list, absent_list, no_obs_list

def remove_bom(s):
    return s.replace('\ufeff', '').strip()

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        user_id = remove_bom(request.form.get("user_id", ""))
        password = remove_bom(request.form.get("password", ""))

        try:
            df_check = pd.read_csv(BASE_URL + "check.csv", dtype=str, encoding='utf-8-sig')
            df_check.iloc[:, 0] = df_check.iloc[:, 0].apply(remove_bom)
            df_check.iloc[:, 1] = df_check.iloc[:, 1].apply(remove_bom)
        except Exception as e:
            error = f"認証データの読み込みに失敗しました: {e}"
            return render_template('login.html', error=error)

        if ((df_check.iloc[:, 0] == user_id) & (df_check.iloc[:, 1] == password)).any():
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            error = 'IDまたはパスワードが正しくありません。'

    return render_template('login.html', error=error)


@app.route('/index', methods=['GET', 'POST'])
def index():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    global observation_table_global, detail_data_global
    df = None
    filtered_df = None
    error = None
    message = None
    course_codes = []
    selected_code = None
    detail_data = []
    grid_data = []
    var_a = var_b = ""
    table_options = []
    selected_table = ""
    empty_list = []
    absent_list = []
    no_obs_list = []
    observation_table = None

    if request.method == "POST":
        var_a = request.form.get("var_a", "")
        var_b = request.form.get("var_b", "")
        selected_code = request.form.get("var_c", "")
        selected_table = request.form.get("selected_table", "")
        action = request.form.get("action")

        session['ver_a'] = var_a
        session['ver_b'] = var_b
        session['ver_c'] = selected_code
        session['selected_table'] = selected_table

        if action == "search" and var_a and var_b:
            filename = f"SCTdat_set_{var_a}_{var_b}.csv"
            file_url = f"{BASE_URL}/{filename}"
            try:
                response = requests.get(file_url)
                response.raise_for_status()
                df = read_csv_with_encoding_auto(response.content)
                message = f"{filename} が見つかりました。"
                course_codes = df.iloc[:, 4].dropna().unique().tolist()
            except Exception as e:
                error = f"エラー: {e}"

        elif action in ["select", "show_table"] and var_a and var_b:
            filename = f"SCTdat_set_{var_a}_{var_b}.csv"
            file_url = f"{BASE_URL}/{filename}"
            try:
                response = requests.get(file_url)
                response.raise_for_status()
                df = read_csv_with_encoding_auto(response.content)
                course_codes = df.iloc[:, 4].dropna().unique().tolist()
                filtered_df = df[df.iloc[:, 4] == selected_code]

                if len(filtered_df) < 2:
                    error = "観察データが2以上でないと表示できません"
                    filtered_df = None
                else:
                    filtered_df = filtered_df.iloc[1:].reset_index(drop=True)
                    linked_filename = df.iloc[0, 2]
                    detail_url = f"{BASE_URL}/{linked_filename}.csv"
                    detail_response = requests.get(detail_url)
                    detail_response.raise_for_status()
                    detail_df = read_csv_with_encoding_auto(detail_response.content)
                    detail_data = [f"C{i+1}: {detail_df.iloc[i, 0]}" for i in range(min(12, len(detail_df)))]
                    detail_data_global = detail_data
                    grid_data, empty_list, absent_list, no_obs_list = create_display_grid(filtered_df)
                    valid_numbers = []
                    for i in range(1, 49):
                        if str(i) not in empty_list + absent_list + no_obs_list:
                            valid_numbers.append(f"S{i}")
                    if "49" not in empty_list + absent_list + no_obs_list:
                        valid_numbers.append("教師")
                    table_options = valid_numbers + [f"C{i}" for i in range(1, 13)] + ["summary"]

                    if action == "show_table" and selected_table:
                        if selected_table.startswith("S") or selected_table == "教師":
                            seat_number = 49 if selected_table == "教師" else int(selected_table[1:])
                            col_index = 10 + seat_number 
                            display_rows = filtered_df.iloc[:, [5, 6, col_index] + list(range(60, 72))].copy()
                            label = "教師" if selected_table == "教師" else selected_table
                            display_rows.columns = ["観察開始時刻", "観察終了時刻", label] + [f"C{i}" for i in range(1, 13)]

                            for c in display_rows.columns[3:]:
                                display_rows[c] = display_rows[c].astype("object")

                            for idx, row in display_rows.iterrows():
                                if row[label] == 0:
                                    for c in display_rows.columns[3:]:
                                        display_rows.at[idx, c] = "."
                            sums = display_rows.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').sum(skipna=True)
                            counts = display_rows.iloc[:, 2:].apply(lambda col: col.apply(lambda x: 1 if x in [0, 1] else 0)).sum()
                            percents = sums / counts * 100
                            sum_row = ["", "sum"] + [int(s) if not pd.isna(s) else "" for s in sums.tolist()]
                            percent_row = ["", "%"] + [f"{p:.1f}%" if c > 0 else "-" for p, c in zip(percents, counts)]
                            display_rows.loc[len(display_rows)] = sum_row
                            display_rows.loc[len(display_rows)] = percent_row
                            observation_table = display_rows

                        elif selected_table.startswith("C"):
                            c_index = 60 + int(selected_table[1:]) - 1
                            seat_cols = []
                            seat_labels = []
                            for i in range(1, 50): # S1からS49（教師）まで
                                current_seat_label = "教師" if i == 49 else f"S{i}"
                                if str(i) not in empty_list + absent_list + no_obs_list:
                                    seat_cols.append(10 + i) # S1なら11, 教師なら59
                                    seat_labels.append(current_seat_label)

                            display_cols = [5, 6, c_index] + seat_cols
                            display_rows = filtered_df.iloc[:, display_cols].copy()
                            display_rows.columns = ["観察開始時刻", "観察終了時刻", selected_table] + seat_labels

                            for s in seat_labels:
                                display_rows[s] = display_rows[s].astype("object")

                            for idx, row in display_rows.iterrows():
                                if row[selected_table] == 0:
                                    for s in seat_labels:
                                        display_rows.at[idx, s] = "."
                            sums = display_rows.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').sum(skipna=True)
                            counts = display_rows.iloc[:, 2:].apply(lambda col: col.apply(lambda x: 1 if x in [0, 1] else 0)).sum()
                            percents = sums / counts * 100
                            sum_row = ["", "sum"] + [int(s) if not pd.isna(s) else "" for s in sums.tolist()]
                            percent_row = ["", "%"] + [f"{p:.1f}%" if c > 0 else "-" for p, c in zip(percents, counts)]
                            display_rows.loc[len(display_rows)] = sum_row
                            display_rows.loc[len(display_rows)] = percent_row
                            observation_table = display_rows

                        elif selected_table == "summary":
                            display_rows = filtered_df.iloc[:, [5, 6] + list(range(60, 72))].copy()
                            display_rows.columns = ["観察開始時刻", "観察終了時刻"] + [f"C{i}" for i in range(1, 13)]
                            sums = display_rows.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').sum(skipna=True)
                            counts = display_rows.iloc[:, 2:].apply(lambda col: col.apply(lambda x: 1 if x in [0, 1] else 0)).sum()
                            percents = sums / counts * 100
                            sum_row = ["", "sum"] + [int(s) if not pd.isna(s) else "" for s in sums.tolist()]
                            percent_row = ["", "%"] + [f"{p:.1f}%" if c > 0 else "-" for p, c in zip(percents, counts)]
                            display_rows.loc[len(display_rows)] = sum_row
                            display_rows.loc[len(display_rows)] = percent_row
                            observation_table = display_rows

                        observation_table_global = observation_table

            except Exception as e:
                error = f"エラー: {e}"

    return render_template(
        "index.html",
        error=error,
        message=message,
        course_codes=course_codes,
        selected_code=selected_code,
        detail_data=detail_data,
        grid_data=grid_data,
        empty_list=empty_list or ["なし"],
        absent_list=absent_list or ["なし"],
        no_obs_list=no_obs_list or ["なし"],
        table_options=table_options,
        selected_table=selected_table,
        var_a=var_a,
        var_b=var_b,
        observation_table=observation_table,
        scroll_to_table = (request.method == "POST" and request.form.get("action") == "show_table" and observation_table is not None)
    )

@app.route("/download/xlsx")
def download_xlsx():
    global observation_table_global
    if observation_table_global is None:
        return "No data to download"
    ver_a = session.get('ver_a', 'unknown')
    ver_b = session.get('ver_b', 'unknown')
    ver_c = session.get('ver_c', 'unknown')
    selected_table = session.get('selected_table', 'unknown')
    filename = f"table_{ver_a}_{ver_b}_{ver_c}_{selected_table}.xlsx"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        observation_table_global.to_excel(tmp.name, index=False)
        return send_file(tmp.name, as_attachment=True, download_name=filename)

@app.route("/download/html")
def download_html():
    global observation_table_global, detail_data_global
    if observation_table_global is None:
        return "No data to download"

    ver_a = session.get('ver_a', 'unknown')
    ver_b = session.get('ver_b', 'unknown')
    ver_c = session.get('ver_c', 'unknown')
    selected_table = session.get('selected_table', 'unknown')
    filename = f"table_{ver_a}_{ver_b}_{ver_c}_{selected_table}.html"

    image_path = os.path.join("static", "ORUTCHI_logo.png")
    with open(image_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode('utf-8')

    table_html = observation_table_global.to_html(index=False)

    if detail_data_global:
        detail_html = "<h4>観察カテゴリ一覧</h4><ul>"
        for item in detail_data_global:
            detail_html += f"<li>{item}</li>"
        detail_html += "</ul>"
    else:
        detail_html = ""

    full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>観察データ出力</title>
</head>
<body>
  <img src="data:image/png;base64,{encoded_image}" alt="ロゴ画像" style="width:200px;"><br><br>
  {table_html}
  <br>
  {detail_html}
</body>
</html>
"""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as tmp:
        tmp.write(full_html)
        tmp_path = tmp.name

    return send_file(tmp_path, as_attachment=True, download_name=filename)
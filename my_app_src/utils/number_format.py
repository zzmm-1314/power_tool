"""模拟结算单 V2 数字格式"""


def apply_number_format_v2(ws):
    three_dec_cols = [2, 3, 5, 7, 9, 10, 11, 12, 14, 15, 16, 17, 19, 20, 21, 22]
    two_dec_cols = [4, 8, 13, 18, 23]
    for row in range(5, 53):
        for col in three_dec_cols:
            try:
                ws.cell(row=row, column=col).number_format = "0.000"
            except Exception:
                pass
        for col in two_dec_cols:
            try:
                ws.cell(row=row, column=col).number_format = "0.00"
            except Exception:
                pass

import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import date, timedelta
from textwrap import dedent

st.set_page_config(layout="wide")

 # ✅ Patch 2: تابع get_status بهبود‌یافته
# Patch 2: get_status ✅ تابع کاملاً هوشمند
def get_status(row):
    import re

    val = row.get("value")

    if pd.isna(val):
        return "Normal"

    if not pd.api.types.is_number(val):
        val_str = str(val).lower()
        if any(word in val_str for word in ["pos", "reactive", "detected", "present"]):
            return "High"
        return "Normal"

    ref_text = row.get("reference_full_text", "")

    def extract_desc(line_str):
        line_str = line_str.strip()
        if ":" in line_str:
            left, right = [p.strip() for p in line_str.split(":", 1)]
            if re.search(r'\d', left):
                return right if right else "Normal"
            else:
                return left if left else "Normal"
        else:
            clean = re.sub(
                r'[<>≤≥]?\s*\d+\.?\d*\s*(?:[–-]\s*\d+\.?\d*)?|[Uu]p\s+[Tt]o\s+\d+\.?\d*',
                '',
                line_str,
                flags=re.IGNORECASE
            ).strip()
            return clean if clean else "Normal"

    if pd.notnull(ref_text) and str(ref_text).strip() != "":
        lines = str(ref_text).strip().split('\n')

        for line in lines:
            line = line.strip()

            # range a–b
            range_match = re.search(r'(\d+\.?\d*)\s*[–-]\s*(\d+\.?\d*)', line)
            if range_match:
                low_val = float(range_match.group(1))
                high_val = float(range_match.group(2))
                if low_val <= val <= high_val:
                    return extract_desc(line)
                continue

            # < number
            lt_match = re.search(r'[<≤]\s*(\d+\.?\d*)', line)
            if lt_match:
                num = float(lt_match.group(1))
                if val < num:
                    return extract_desc(line)
                continue

            # > number
            gt_match = re.search(r'[>≥]\s*(\d+\.?\d*)', line)
            if gt_match:
                num = float(gt_match.group(1))
                if val > num:
                    return extract_desc(line)
                continue

            # Up to number
            up_to_match = re.search(r'[Uu]p\s+[Tt]o\s+(\d+\.?\d*)', line)
            if up_to_match:
                num = float(up_to_match.group(1))
                if val <= num:
                    return extract_desc(line)
                else:
                    return "High"

    # fallback
    low = row.get("ref_low")
    high = row.get("ref_high")

    if pd.notnull(low) and val < low:
        return "Low"
    if pd.notnull(high) and val > high:
        return "High"

    return "Normal"
        
def parse_multi_range(ref_text):
    """
    استخراج بازه‌های reference_full_text
    """
    import re
    
    if pd.isna(ref_text) or str(ref_text).strip() == "":
        return []
    
    ref_text = str(ref_text).strip()
    
    # ✅ جدا کردن خطوط
    lines = ref_text.split('\n')
    
    # اگر فقط یک خط بود و : دارد
    if len(lines) == 1 and ':' in ref_text:
        # تقسیم بر اساس pattern: هر جا که یک description جدید شروع می‌شه
        lines = re.split(r'(?<=\d)(?=[A-Za-z])|(?<=[a-z])(?=[A-Z<>≤≥])', ref_text)
    
    lines = [l.strip() for l in lines if l.strip()]
    
    result = []
    
    for line in lines:
        # تعیین description و condition
        if ':' in line:
            parts = line.split(':', 1)
            left = parts[0].strip()
            right = parts[1].strip()
            
            # اگر سمت چپ عملگر دارد (<, >, ≤, ≥, عدد-عدد)
            if re.search(r'[<>≤≥]|\d+\s*[–-]\s*\d+|[Uu]p\s+[Tt]o', left):
                condition = left
                description = right
            else:
                description = left
                condition = right
        else:
            condition = line
            description = ""
        
        # ✅ حالت 1: a–b
        range_match = re.search(r'(\d+\.?\d*)\s*[–-]\s*(\d+\.?\d*)', condition)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            result.append({
                'description': description,
                'low': low,
                'high': high,
                'type': 'range'
            })
            continue
        
        # ✅ حالت 2: <number یا ≤number
        lt_match = re.search(r'[<≤]\s*(\d+\.?\d*)', condition)
        if lt_match:
            num = float(lt_match.group(1))
            result.append({
                'description': description,
                'low': None,
                'high': num,
                'type': 'lt'
            })
            continue
        
        # ✅ حالت 3: >number یا ≥number
        gt_match = re.search(r'[>≥]\s*(\d+\.?\d*)', condition)
        if gt_match:
            num = float(gt_match.group(1))
            result.append({
                'description': description,
                'low': num,
                'high': None,
                'type': 'gt'
            })
            continue
        
        # ✅ حالت 4: Up to NUMBER
        up_to_match = re.search(r'[Uu]p\s+[Tt]o\s+(\d+\.?\d*)', condition)
        if up_to_match:
            num = float(up_to_match.group(1))
            result.append({
                'description': description if description else "Normal",
                'low': 0,  # ✅ FIX: شروع از صفر
                'high': num,
                'type': 'range'  # ✅ FIX: تبدیل به range به جای up_to
            })
            continue
    
    return result

def get_zone_color(ranges, val):
    """
    تعیین رنگ زون برای هر بازه
    اولین (کمترین) زون: نارنجی (#FF8C00)
    آخرین (بیشترین) زون: قرمز (#FF4444)
    میانی: سبز (#6ee7b7)
    """
    if not ranges:
        return None
    
    n = len(ranges)
    
    # تعیین رنگ هر زون
    colors = []
    for i, r in enumerate(ranges):
        if i == 0 and r['type'] in ['lt', 'up_to']:
            # اولین زون (کمترین) → نارنجی
            colors.append('#FF8C00')
        elif i == n - 1 and r['type'] == 'gt':
            # آخرین زون (بیشترین) → قرمز
            colors.append('#FF4444')
        elif i == 0 and r['type'] == 'gt':
            # اگر اولین زون > بود → قرمز
            colors.append('#FF4444')
        elif i == n - 1 and r['type'] in ['lt', 'up_to']:
            # اگر آخرین زون < بود → نارنجی
            colors.append('#FF8C00')
        else:
            # میانی → سبز
            colors.append('#6ee7b7')
    
    return colors
    
        
# ✅ تابع تبدیل تاریخ شمسی به میلادی
def convert_date_to_gregorian(date_input):
    """تبدیل تاریخ شمسی یا میلادی به فرمت استاندارد YYYY-MM-DD"""
    if pd.isna(date_input):
        return pd.Timestamp.now().strftime('%Y-%m-%d')
    
    date_str = str(date_input).strip()
    
    # تلاش برای تاریخ میلادی
    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except:
        pass
    
    # تلاش برای تاریخ شمسی (مثلاً 1404-04-31)
    try:
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                
                # آرایه روزهای ماه‌های شمسی
                j_days_in_month = [31,31,31,31,31,31, 30,30,30,30,30,29]
                
                # محاسبه تعداد روز از مبدأ
                gy = jy + 621
                
                # روزهای سپری‌شده از ابتدای سال شمسی
                j_day_of_year = jd
                for i in range(jm - 1):
                    j_day_of_year += j_days_in_month[i]
                
                # ابتدای سال شمسی jy تقریباً 21 مارس سال gy
                march_21 = date(gy, 3, 21)
                result_date = march_21 + timedelta(days=j_day_of_year - 1)
                
                return result_date.strftime('%Y-%m-%d')
    except:
        pass
    
    return date_str

def parse_reference_range(ref_text):
    """
    استخراج حد پایین و بالا از متن reference
    برای شرایط <200 و >240 را نادیده می‌گیرد
    فقط محدوده‌های بسته (a–b) را استخراج می‌کند
    """
    import re
    
    if pd.isna(ref_text) or ref_text == "":
        return None, None
    
    ref_text = str(ref_text).strip()
    
    # جستجوی محدوده‌های بسته (a–b)
    range_matches = re.findall(r'(\d+\.?\d*)\s*[–-]\s*(\d+\.?\d*)', ref_text)
    
    if len(range_matches) == 0:
        # اگر محدوده بسته نیست، None برگردان
        return None, None
    
    # تمام محدوده‌های بسته
    all_numbers = []
    for low_str, high_str in range_matches:
        all_numbers.append(float(low_str))
        all_numbers.append(float(high_str))
    
    # کمترین و بیشترین عدد
    ref_low = min(all_numbers)
    ref_high = max(all_numbers)
    
    return ref_low, ref_high
    
 
st.set_page_config(layout="wide")
    
st.title("🏥 Lab Dashboard")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# ✅ تابع ساخت بولت‌چارت
def create_clinical_range_chart(row, pdf_mode=False, width=None):
    import re
    
    val = row["value"]
    
    if pd.isna(val) or not pd.api.types.is_number(val):
        return None
    
    ref_text = row.get("reference_full_text", "")
    
    # ✅ اول بررسی reference_full_text
    if pd.notnull(ref_text) and str(ref_text).strip() != "":
        ranges = parse_multi_range(str(ref_text))
        
        if len(ranges) >= 1:
            return create_multi_range_chart(row, ranges, pdf_mode, width)
    
    # ✅ سپس بررسی ref_low و ref_high
    ref_low = row.get("ref_low")
    ref_high = row.get("ref_high")
    
    if pd.notnull(ref_text) and str(ref_text).strip() != "":
        ranges = parse_multi_range(str(ref_text))

        if len(ranges) >= 1:
            return create_multi_range_chart(row, ranges, pdf_mode, width)

        # ✅ FIX: اگر multi-range نتوانست بازه بسازد، از range ساده استفاده کن
        ref_low_fallback, ref_high_fallback = parse_reference_range(ref_text)
        if ref_low_fallback is not None and ref_high_fallback is not None:
            return create_simple_chart(row, ref_low_fallback, ref_high_fallback, pdf_mode, width)    
        return None


def create_simple_chart(row, ref_low, ref_high, pdf_mode=False, width=None):
    """نمودار ساده با یک بازه"""
    val = row["value"]
    
    diff = ref_high - ref_low
    plot_min = min(ref_low - (diff * 0.5), val - (diff * 0.2))
    plot_max = max(ref_high + (diff * 0.5), val + (diff * 0.2))

    if pdf_mode:
        chart_height = 90
        font_size = 9
        margin_side = 100
    else:
        chart_height = 110
        font_size = 13

    fig = px.scatter()
    bar_y0, bar_y1 = 0.12, 0.32
    bar_mid = (bar_y0 + bar_y1) / 2
    zone_min = ref_low - (diff * 0.5)
    zone_max = ref_high + (diff * 0.5)

    fig.add_shape(type="rect", x0=zone_min, x1=ref_low, y0=bar_y0, y1=bar_y1, fillcolor="#fdecea", line_width=0)
    fig.add_shape(type="rect", x0=ref_low, x1=ref_high, y0=bar_y0, y1=bar_y1, fillcolor="#6ee7b7", line_width=0)
    fig.add_shape(type="rect", x0=ref_high, x1=zone_max, y0=bar_y0, y1=bar_y1, fillcolor="#fdecea", line_width=0)

    # ✅ FIX: رنگ status بر اساس نوع تست
    test_name_lower = row['test_name'].lower()
    
    if 'hdl' in test_name_lower and 'ldl' not in test_name_lower:
        # HDL: Low = بد (نارنجی/قرمز), High = خوب (سبز)
        if row["status"] in ["Low", "High Risk"]:
            status_color = "#FF4444"  # قرمز
        elif row["status"] in ["High", "Low Risk"]:
            status_color = "green"
        else:
            status_color = "green"
    else:
        # سایر تست‌ها: Low = نارنجی, High = قرمز, Normal = سبز
        if row["status"] == "Low":
            status_color = "#FF8C00"  # نارنجی
        elif row["status"] in ["High", "High Risk", "Very High"]:
            status_color = "#FF4444"  # قرمز
        elif row["status"] in ["Normal", "Desirable", "Optimal"]:
            status_color = "green"
        else:
            status_color = "green"

    fig.add_annotation(
        xref="paper", x=0, y=bar_mid,
        xshift=-(margin_side if pdf_mode else 150) + 10,
        text=f"<b>{row['test_name']}</b><br><span style='font-size:8px'>{row['unit']}</span>",
        showarrow=False, xanchor="left", yanchor="middle",
        font=dict(size=font_size)
    )
    # ✅ FIX: نمایش status با دایره رنگی
    if row["status"] in ["Normal", "Desirable", "Optimal"]:
        # حالت نرمال: متن سبز بدون دایره
        status_text = f"<b>{row['status']}</b>"
        text_color = "green"
    else:
        # حالت غیرنرمال: متن مشکی + دایره رنگی در انتها
        circle = "●"  # یونیکد U+25CF
        circle_size = int(font_size * 1.5)  # 1.5 برابر سایز متن
        status_text = f"<b>{row['status']}</b> <span style='color:{status_color}; font-size:{circle_size}px'>{circle}</span>"
        text_color = "black"
    
    fig.add_annotation(
        xref="paper", x=1, y=bar_mid,
        xshift=(margin_side if pdf_mode else 80) - 10,
        text=status_text,
        showarrow=False, xanchor="right", yanchor="middle",
        font=dict(size=font_size, color=text_color)
    )
    for r_val in [ref_low, ref_high]:
        fig.add_annotation(
            x=r_val, y=bar_mid, text=str(r_val),
            showarrow=False, font=dict(size=font_size-2, color="#333")
        )

    fig.add_trace(px.scatter(x=[val], y=[bar_y1 + 0.02]).data[0])
    fig.data[-1].update(marker=dict(size=10, symbol="triangle-down", color="black"))
    fig.add_annotation(
        x=val, y=bar_y1 + 0.22, text=f"<b>{val}</b>",
        showarrow=False, font=dict(size=font_size)
    )

    fig.update_layout(
        height=chart_height,
        width=width if pdf_mode else None,
        xaxis=dict(
            range=[plot_min, plot_max],
            showgrid=False, zeroline=False, showline=True, linecolor="black",
            tickfont=dict(size=font_size-3)
        ),
        yaxis=dict(visible=False, range=[0, 0.7]),
        margin=dict(l=margin_side if pdf_mode else 150,
                    r=margin_side if pdf_mode else 80,
                    t=25, b=20),
        template="simple_white"
    )
    return fig

def create_multi_range_chart(row, ranges, pdf_mode=False, width=None):
    """نمودار با چندین بازه رنگی"""
    val = row["value"]
    # ✅ FIX: مرتب سازی بازه ها برای جلوگیری از به هم ریختگی نمودار
    ranges = sorted(
        ranges,
        key=lambda r: (
            float('-inf') if r['low'] is None else r['low']
        )
    )    
    if pdf_mode:
        chart_height = 90
        font_size = 9
        margin_side = 100
    else:
        chart_height = 110
        font_size = 13

    # پیدا کردن حدود نمودار
    all_nums = []
    for r in ranges:
        if r['low'] is not None:
            all_nums.append(r['low'])
        if r['high'] is not None:
            all_nums.append(r['high'])
    
    if not all_nums:
        return None
    
    chart_min = min(all_nums)
    chart_max = max(all_nums)
    diff = chart_max - chart_min
    
    plot_min = min(chart_min - (diff * 0.3), val - (diff * 0.2))
    plot_max = max(chart_max + (diff * 0.3), val + (diff * 0.2))

    # رنگ‌بندی زون‌ها
    n = len(ranges)
    zone_colors_list = []
    for i, r in enumerate(ranges):
        if n == 1:
            zone_colors_list.append('#6ee7b7')
        elif i == 0 and r['type'] in ['lt', 'up_to']:
            zone_colors_list.append('#6ee7b7')  # اولین زون lt → سبز (نرمال)
        elif i == n - 1 and r['type'] == 'gt':
            zone_colors_list.append('#FF4444')  # آخرین زون gt → قرمز
        elif r['type'] == 'lt' and i > 0:
            zone_colors_list.append('#FF8C00')  # lt بعدی → نارنجی
        elif r['type'] == 'gt' and i < n - 1:
            zone_colors_list.append('#FF4444')  # gt قبلی → قرمز
        elif i == 0:
            zone_colors_list.append('#FF8C00')  # اول → نارنجی
        elif i == n - 1:
            zone_colors_list.append('#FF4444')  # آخر → قرمز
        else:
            # میانی → رنگ‌بندی بر اساس موقعیت
            mid = n // 2
            if i < mid:
                zone_colors_list.append('#a8e6cf')  # سبز روشن
            else:
                zone_colors_list.append('#ffd3b6')  # نارنجی روشن

    fig = px.scatter()
    bar_y0, bar_y1 = 0.12, 0.32
    bar_mid = (bar_y0 + bar_y1) / 2

    # رسم زون‌ها
    for i, r in enumerate(ranges):
        color = zone_colors_list[i]
        
        if r['type'] == 'range':
            x0, x1 = r['low'], r['high']
        elif r['type'] in ['lt', 'up_to']:
            x0 = plot_min
            x1 = r['high']
        elif r['type'] == 'gt':
            x0 = r['low']
            x1 = plot_max
        else:
            continue
        
        fig.add_shape(
            type="rect",
            x0=x0, x1=x1,
            y0=bar_y0, y1=bar_y1,
            fillcolor=color,
            line_width=0.5,
            line_color="white"
        )
        
        # label هر زون روی نوار
        mid_x = (x0 + x1) / 2
        if r['description']:
            short_desc = r['description'][:12] if len(r['description']) > 8 else r['description']
            fig.add_annotation(
                x=mid_x, y=bar_y0 - 0.06,
                text=f"<span style='font-size:10px'>{short_desc}</span>",
                showarrow=False,
                font=dict(size=8, color="#555"),
                xanchor="center"
            )

    # نام تست در چپ
    fig.add_annotation(
        xref="paper", x=0, y=bar_mid,
        xshift=-(margin_side if pdf_mode else 150) + 10,
        text=f"<b>{row['test_name']}</b><br><span style='font-size:8px'>{row['unit']}</span>",
        showarrow=False, xanchor="left", yanchor="middle",
        font=dict(size=font_size)
    )

    # ✅ وضعیت در راست
    status = row["status"]
    test_name_lower = row['test_name'].lower()
    
    # ✅ FIX 1: HDL Cholesterol - معکوس کردن رنگ‌ها
    if 'hdl' in test_name_lower and 'ldl' not in test_name_lower:
        # برای HDL: Low = بد (قرمز)، High = خوب (سبز)
        if status == "High Risk":
            status_color = "#FF4444"  # قرمز
        elif status == "Low Risk":
            status_color = "green"
        else:
            # پیدا کردن رنگ از زون‌ها
            status_color = "green"
            for i, r in enumerate(ranges):
                if r['description'] == status:
                    # معکوس کردن رنگ
                    if zone_colors_list[i] == '#6ee7b7':
                        status_color = '#FF4444'
                    elif zone_colors_list[i] == '#FF4444':
                        status_color = 'green'
                    else:
                        status_color = zone_colors_list[i]
                    break
    else:
        # ✅ FIX 2: سایر تست‌ها - رنگ بر اساس status
        if status == "Low":
            status_color = "#FF8C00"  # نارنجی
        elif status in ["High", "High Risk", "Very High"]:
            status_color = "#FF4444"  # قرمز
        else:
            # پیدا کردن رنگ از زون‌ها
            status_color = "green"
            for i, r in enumerate(ranges):
                if r['description'] == status:
                    status_color = zone_colors_list[i]
                    break
            
            # اگر رنگ سبز روشن است، به سبز تیره تبدیل کن
            if status_color == '#6ee7b7':
                status_color = 'green'

    # ✅ FIX: نمایش status با دایره رنگی
    if status in ["Normal", "Desirable", "Optimal", "Low Risk"]:
        # حالت نرمال: متن سبز بدون دایره
        status_text = f"<b>{status}</b>"
        text_color = "green"
    else:
        # حالت غیرنرمال: متن مشکی + دایره رنگی در انتها
        circle = "●"  # یونیکد U+25CF
        circle_size = int(font_size * 1.5)  # 1.5 برابر سایز متن
        status_text = f"<b>{status}</b> <span style='color:{status_color}; font-size:{circle_size}px'>{circle}</span>"
        text_color = "black"
    
    fig.add_annotation(
        xref="paper", x=1, y=bar_mid,
        xshift=(margin_side if pdf_mode else 80) - 10,
        text=status_text,
        showarrow=False, xanchor="right", yanchor="middle",
        font=dict(size=font_size, color=text_color)
    )
    
    # مثلث مقدار
    fig.add_trace(px.scatter(x=[val], y=[bar_y1 + 0.02]).data[0])
    fig.data[-1].update(marker=dict(size=10, symbol="triangle-down", color="black"))
    fig.add_annotation(
        x=val, y=bar_y1 + 0.22,
        text=f"<b>{val}</b>",
        showarrow=False, font=dict(size=font_size)
    )

    fig.update_layout(
        height=chart_height,
        width=width if pdf_mode else None,
        xaxis=dict(
            range=[plot_min, plot_max],
            showgrid=False, zeroline=False, showline=True, linecolor="black",
            tickfont=dict(size=font_size-3)
        ),
        yaxis=dict(visible=False, range=[0, 0.7]),
        margin=dict(l=margin_side if pdf_mode else 150,
                    r=margin_side if pdf_mode else 80,
                    t=25, b=20),
        template="simple_white"
    )
    return fig

if uploaded_file is not None:
    
    df = pd.read_excel(uploaded_file)
    row = df[df["test_name"]=="LDL Cholesterol"].iloc[0]
    df = df.reset_index(drop=True)
    if "is_numeric" in df.columns:
        df["is_numeric"] = pd.to_numeric(df["is_numeric"], errors="coerce").fillna(1).astype(int)
    # if "is_numeric" in df.columns:
        # df["is_numeric"] = pd.to_numeric(df["is_numeric"], errors="coerce").fillna(1)
    # print(df["is_numeric"].dtype)
    # print(df["is_numeric"].unique())
    # --- هوشمندسازی ستون‌ها ---
    column_map = {
        'Test': 'test_name', 'Parameter': 'test_name',
        'Result': 'value', 'Value': 'value',
        'Ref Low': 'ref_low', 'Min': 'ref_low',
        'Ref High': 'ref_high', 'Max': 'ref_high',
        'Unit': 'unit'
    }
    df = df.rename(columns=column_map)

    # ✅ همیشه از reference_full_text استخراج کن
    if "reference_full_text" in df.columns:
        parsed_ranges = df["reference_full_text"].apply(parse_reference_range)
        df["ref_low"] = parsed_ranges.apply(lambda x: x[0])
        df["ref_high"] = parsed_ranges.apply(lambda x: x[1])

    # ✅ Patch 1: استخراج ستاره و ذخیره به‌صورت جداگانه
    df["footnote"] = ""
    df["value_clean"] = df["value"].astype(str).apply(lambda x: x.rstrip("*"))
    df["has_asterisk"] = df["value"].astype(str).str.endswith("*")
    
    footnote_map = {
        True: "* = The results were rechecked. If clinically not expected, it is recommended to repeat the test."
    }
    df["footnote"] = df["has_asterisk"].map(footnote_map).fillna("")
    
    df["value"] = pd.to_numeric(df["value_clean"], errors="coerce")

    # استخراج اطلاعات پایه
    patient_name = df["patient_name"].iloc[0] if 'patient_name' in df.columns else "Unknown"
    raw_date = df["report_date"].iloc[0] if 'report_date' in df.columns else pd.Timestamp.now()
    report_date = convert_date_to_gregorian(raw_date)
    
    # ✅ استخراج ref_low و ref_high از reference_full_text
    if "reference_full_text" in df.columns:
        parsed_ranges = df["reference_full_text"].apply(parse_reference_range)

        df["ref_low_parsed"] = parsed_ranges.apply(lambda x: x[0])
        df["ref_high_parsed"] = parsed_ranges.apply(lambda x: x[1])

        df["ref_low"] = df["ref_low"].combine_first(df["ref_low_parsed"])
        df["ref_high"] = df["ref_high"].combine_first(df["ref_high_parsed"])
        
        # استفاده از مقادیر استخراج‌شده اگر ref_low/ref_high خالی باشند
        df["ref_low"] = df["ref_low"].fillna(df["ref_low_parsed"])
        df["ref_high"] = df["ref_high"].fillna(df["ref_high_parsed"])
    else:
        df["ref_low_parsed"] = None
        df["ref_high_parsed"] = None
 
    df["value"] = pd.to_numeric(df["value_clean"], errors="coerce")

    # ✅ محاسبه status
    df["status"] = df.apply(get_status, axis=1)
    
    def format_result_with_asterisk(row):
        value_str = str(row.get("value_clean", "")).strip()
        val_lower = value_str.lower()

        # ✅ Positive qualitative marker
        positive_variants = ["positive", "poisitive", "pos", "+", "++", "+++"]
        if (
            "positive" in val_lower
            or "poisitive" in val_lower
            or val_lower in positive_variants
        ):
            value_str = f"{value_str} ➕"

        # ✅ Asterisk
        if row.get("has_asterisk", False):
            value_str += "*"

        # ✅ High / Low markers
        status = str(row.get("status", ""))

        if status in ["High", "High Risk", "Very High"]:
            return f"{value_str} 🔺"
        elif status == "Low":
            return f"{value_str} 🔻"
        else:
            return value_str
    
    def build_display_table(df_input):
        df_display = df_input.copy()

        # Result formatting
        df_display["value"] = df_display.apply(format_result_with_asterisk, axis=1)

        # Unit formatting
        if "unit" in df_display.columns:
            df_display["unit"] = (
                df_display["unit"]
                .astype("object")
                .replace(["", "nan", "NaN", "None"], pd.NA)
                .fillna("-")
            )
        else:
            df_display["unit"] = "-"

        # Reference Range
        df_display["Reference Range"] = ""

        if "reference_full_text" in df_display.columns:
            df_display["Reference Range"] = df_display["reference_full_text"]

        if "ref_low" in df_display.columns and "ref_high" in df_display.columns:
            fallback_ref = (
                df_display["ref_low"].astype(str)
                + " - "
                + df_display["ref_high"].astype(str)
            )

            blank_ref_mask = (
                df_display["Reference Range"].isna()
                | df_display["Reference Range"].astype(str).str.strip().isin(["", "nan", "NaN", "None"])
            )

            df_display.loc[blank_ref_mask, "Reference Range"] = fallback_ref[blank_ref_mask]

        df_display["Reference Range"] = (
            df_display["Reference Range"]
            .fillna("")
            .astype(str)
            .replace({
                "nan": "",
                "NaN": "",
                "None": "",
                "nan - nan": "",
                "None - None": ""
            })
        )

        df_display = df_display[["test_name", "value", "unit", "Reference Range"]]
        df_display.columns = ["Test", "Result", "Unit", "Reference Range"]

        return df_display    
        
    def render_html_table(display_df, css_style):
        display_df_html = display_df.copy()

        if "Reference Range" in display_df_html.columns:
            display_df_html["Reference Range"] = (
                display_df_html["Reference Range"]
                .fillna("")
                .astype(str)
                .str.replace('\n', '<br>', regex=False)
            )

        html_table = display_df_html.to_html(
            index=False,
            escape=False,
            classes="lab-table"
        )

        st.markdown(css_style + html_table, unsafe_allow_html=True)        
        
    def render_footnotes(df_input):
        if "footnote" not in df_input.columns:
            return

        footnotes = df_input[df_input["footnote"] != ""]["footnote"].unique()

        if len(footnotes) > 0:
            st.caption("---")
            for note in footnotes:
                st.caption(f"_{note}_")
            
    def render_pie_chart(df_input, title):
        percentage_df = df_input[
            (df_input.get("is_numeric", 1) == 3) &
            (df_input["value"].notna())
        ].copy()

        if percentage_df.empty:
            return

        st.markdown(f"### 📊 {title} - Distribution")

        fig_pie = px.pie(
            percentage_df,
            values="value",
            names="test_name",
            hole=0.4
        )

        fig_pie.update_traces(
            textposition='outside',
            texttemplate='<b>%{label}</b><br>%{value:.2f}%',
            textfont=dict(size=10, family="Arial"),
            hovertemplate='<b>%{label}</b><br>Value: %{value:.2f}%<extra></extra>',
            marker=dict(
                line=dict(color='white', width=2),
                colors=px.colors.qualitative.Pastel
            )
        )

        fig_pie.update_layout(
            height=400,
            width=500,
            showlegend=False,
            font=dict(size=10),
            margin=dict(l=150, r=150, t=50, b=50)
        )

        st.plotly_chart(fig_pie, width="content")


    def render_bullet_charts(df_input):
        for _, row in df_input.iterrows():

            try:
                row_is_numeric = int(row.get("is_numeric", 1))
            except:
                row_is_numeric = 1

            # 0 = no chart
            # 3 = pie only
            if row_is_numeric in [0, 3]:
                continue

            has_ref_text = (
                pd.notnull(row.get("reference_full_text"))
                and str(row.get("reference_full_text", "")).strip() != ""
            )

            has_ref_range = (
                pd.notnull(row.get("ref_low"))
                and pd.notnull(row.get("ref_high"))
            )

            is_numeric_val = (
                pd.notnull(row.get("value"))
                and pd.api.types.is_number(row.get("value"))
            )

            if is_numeric_val and (has_ref_text or has_ref_range):
                fig = create_clinical_range_chart(row, pdf_mode=False)

                if fig:
                    st.plotly_chart(
                        fig,
                        width="stretch",
                        config={'displayModeBar': False}
                    )
    
    # ✅ تست قطعی LDL
    row = df[df["test_name"] == "LDL Cholesterol"].iloc[0]
    
    # ✅ Summary
    st.subheader("📊 Summary")

    normal_tests = df[df["status"] == "Normal"]["test_name"].tolist()
    high_tests = df[df["status"] == "High"]["test_name"].tolist()
    low_tests = df[df["status"] == "Low"]["test_name"].tolist()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("✅ Normal", len(normal_tests))
        # ✅ FIX: بدون نمایش نام تست‌های نرمال

    with col2:
        st.metric("🔺 High", len(high_tests))
        if high_tests:
            st.caption(", ".join(high_tests))  # همه تست‌های High

    with col3:
        st.metric("🔻 Low", len(low_tests))
        if low_tests:
            st.caption(", ".join(low_tests))  # همه تست‌های Low

    st.divider()

    categories = df["category"].unique()

    # ✅ CSS Style یک بار تعریف کنید
    css_style = """
<style>
.lab-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0px;
    font-size: 13px;
}
.lab-table th {
    background-color: #d3d3d3;
    padding: 10px;
    text-align: left;
    border: 1px solid #999;
    font-weight: bold;
}
.lab-table td {
    padding: 10px;
    border: 1px solid #ddd;
    vertical-align: top;
    white-space: pre-wrap;
    word-wrap: break-word;
}
.lab-table tr:nth-child(even) {
    background-color: #f9f9f9;
}
</style>
"""

    # ✅ نمایش در صفحه (Dashboard)
    for cat in categories:

        df_cat = df[df["category"] == cat]

        if df_cat.empty:
            continue

        # ✅ عنوان همیشه اول
        st.markdown(f"## 🧪 {cat}")

        # بررسی sub_category
        if "sub_category" in df_cat.columns:
            sub_cats = (
                df_cat["sub_category"]
                .replace(["nan", "NaN", "None", ""], pd.NA)
                .dropna()
                .unique()
            )
            has_sub = len(sub_cats) > 0
        else:
            has_sub = False
            sub_cats = []

        # ==========================================
        # با sub_category
        # ==========================================
        if has_sub:

            for sub in sub_cats:

                df_sub = df_cat[df_cat["sub_category"] == sub]

                if df_sub.empty:
                    continue

                st.subheader(f"🔬 {sub}")

                col_left, col_right = st.columns([1, 1.2])

                # ---------- LEFT: Table + Pie ----------
                with col_left:
                    sub_display = build_display_table(df_sub)
                    render_html_table(sub_display, css_style)
                    render_footnotes(df_sub)
                    render_pie_chart(df_sub, sub)

                # ---------- RIGHT: Bullet Charts ----------
                with col_right:
                    render_bullet_charts(df_sub)

                st.divider()

        # ==========================================
        # بدون sub_category
        # ==========================================
        else:

            col_left, col_right = st.columns([1, 1.2])

            # ---------- LEFT: Table + Pie ----------
            with col_left:
                display_df = build_display_table(df_cat)
                render_html_table(display_df, css_style)
                render_footnotes(df_cat)
                render_pie_chart(df_cat, cat)

            # ---------- RIGHT: Bullet Charts ----------
            with col_right:
                render_bullet_charts(df_cat)

            st.divider()
    
    # ✅ ساخت PDF
    with st.sidebar:
        st.write("### 📥 Export Options")
        buffer = BytesIO()
        PAGE_MARGIN = 50
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=PAGE_MARGIN, 
            leftMargin=PAGE_MARGIN, 
            topMargin=PAGE_MARGIN, 
            bottomMargin=PAGE_MARGIN
        )
        
        AVAILABLE_WIDTH = A4[0] - 2 * PAGE_MARGIN 
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Mashhad Pathobiology Lab", styles["Heading1"]))
        elements.append(Spacer(1, 8))

        elements.append(Paragraph(
            f"<b>Patient Name:</b> {patient_name} &nbsp;&nbsp;&nbsp;&nbsp;"
            f"<b>Report Date:</b> {report_date}",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 15))
        
        # ✅ اضافه کردن Summary
        elements.append(Paragraph("📊 Summary", styles["Heading2"]))
        elements.append(Spacer(1, 8))
        
        # محاسبه تعداد تست‌ها
        normal_tests = df[df["status"] == "Normal"]["test_name"].tolist()
        high_tests = df[df["status"] == "High"]["test_name"].tolist()
        low_tests = df[df["status"] == "Low"]["test_name"].tolist()
        
        # ایجاد جدول Summary
        summary_data = [
            ["Status", "Count", "Tests"],
            ["✅ Normal", str(len(normal_tests)), ", ".join(normal_tests[:5]) + ("..." if len(normal_tests) > 5 else "")],
            ["🔺 High", str(len(high_tests)), ", ".join(high_tests[:5]) + ("..." if len(high_tests) > 5 else "")],
            ["🔻 Low", str(len(low_tests)), ", ".join(low_tests[:5]) + ("..." if len(low_tests) > 5 else "")]
        ]
        
        summary_table = Table(
            summary_data,
            colWidths=[AVAILABLE_WIDTH * 0.20, AVAILABLE_WIDTH * 0.15, AVAILABLE_WIDTH * 0.65]
        )
        
        # رنگ‌بندی ردیف‌ها
        summary_table.setStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), 'LEFT'),
            ("FONTNAME", (0, 0), (-1, 0), 'Helvetica-Bold'),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            
            # ✅ رنگ سبز برای Normal
            ("BACKGROUND", (0, 1), (-1, 1), colors.Color(0.43, 0.91, 0.72, alpha=0.3)),  # #6ee7b7 با شفافیت
            
            # 🔺 رنگ قرمز برای High
            ("BACKGROUND", (0, 2), (-1, 2), colors.Color(1.0, 0.27, 0.27, alpha=0.2)),  # #FF4444 با شفافیت
            
            # 🔻 رنگ نارنجی برای Low
            ("BACKGROUND", (0, 3), (-1, 3), colors.Color(1.0, 0.55, 0.0, alpha=0.2)),  # #FF8C00 با شفافیت
            
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        summary_table.hAlign = 'LEFT'
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # elements.append(Paragraph(
            # f"<b>Patient Name:</b> {patient_name} &nbsp;&nbsp;&nbsp;&nbsp;"
            # f"<b>Report Date:</b> {report_date}",
            # styles["Normal"]
        # ))
        elements.append(Spacer(1, 15))

        for cat in categories:

            df_cat = df[df["category"] == cat]

            if df_cat.empty:
                continue

            elements.append(Paragraph(cat, styles["Heading2"]))
            elements.append(Spacer(1, 6))

            if "sub_category" in df_cat.columns:
                sub_cats = (
                    df_cat["sub_category"]
                    .replace(["nan", "NaN", "None", ""], pd.NA)
                    .dropna()
                    .unique()
                )
                has_sub = len(sub_cats) > 0
            else:
                has_sub = False
                sub_cats = []

            if has_sub:

                for sub in sub_cats:

                    df_sub = df_cat[df_cat["sub_category"] == sub]

                    if df_sub.empty:
                        continue

                    elements.append(Paragraph(f" {sub}", styles["Heading3"]))
                    elements.append(Spacer(1, 4))

                    # ✅ جدول
                    pdf_display = build_display_table(df_sub)

                    table_data = [["Test", "Result", "Unit", "Reference Range"]]

                    for _, row in pdf_display.iterrows():
                        table_data.append([
                            row["Test"],
                            row["Result"],
                            row["Unit"],
                            row["Reference Range"]
                        ])

                    t = Table(
                        table_data,
                        colWidths=[
                            AVAILABLE_WIDTH * 0.35,
                            AVAILABLE_WIDTH * 0.20,
                            AVAILABLE_WIDTH * 0.15,
                            AVAILABLE_WIDTH * 0.30
                        ]
                    )

                    t.setStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ALIGN", (0, 0), (-1, -1), 'LEFT'),
                        ("VALIGN", (0, 0), (-1, -1), 'MIDDLE'),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ])

                    elements.append(t)
                    elements.append(Spacer(1, 10))

                    # ✅ Pie (فقط 3)
                    percentage_sub = df_sub[
                        (df_sub.get("is_numeric", 1) == 3) &
                        (df_sub["value"].notna())
                    ].copy()

                    if not percentage_sub.empty:
                        elements.append(Paragraph(f"{sub} - Distribution", styles["Normal"]))
                        elements.append(Spacer(1, 6))

                        fig_pie = px.pie(
                            percentage_sub,
                            values="value",
                            names="test_name",
                            hole=0.4
                        )
                        
                        fig_pie.update_traces(
                            textposition='outside',
                            texttemplate='<b>%{label}</b><br>%{value:.2f}%',
                            textfont=dict(size=10),
                            marker=dict(
                                line=dict(color='white', width=2),
                                colors=px.colors.qualitative.Pastel
                            )
                        )

                        fig_pie.update_layout(
                            height=400,
                            width=500,
                            showlegend=False,
                            font=dict(size=10),
                            margin=dict(l=150, r=150, t=50, b=50),
                            template="simple_white"
                        )
                        img_bytes = fig_pie.to_image(format="png", scale=2)
                        img = Image(BytesIO(img_bytes))
                        img.drawWidth = AVAILABLE_WIDTH * 0.7
                        img.drawHeight = 280
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 10))

                    # ✅ Bullet
                    for _, row in df_sub.iterrows():

                        row_is_numeric = int(row.get("is_numeric", 1))

                        if row_is_numeric in [0, 3]:
                            continue

                        has_ref_text = pd.notnull(row.get("reference_full_text")) and str(row.get("reference_full_text", "")).strip() != ""
                        has_ref_range = pd.notnull(row.get("ref_low")) and pd.notnull(row.get("ref_high"))
                        is_numeric_val = pd.notnull(row["value"]) and pd.api.types.is_number(row["value"])

                        if is_numeric_val and (has_ref_text or has_ref_range):
                            fig = create_clinical_range_chart(row, pdf_mode=True, width=AVAILABLE_WIDTH * 1.5)

                            if fig:
                                img_bytes = fig.to_image(format="png", scale=2)
                                img = Image(BytesIO(img_bytes))
                                img.drawWidth = AVAILABLE_WIDTH
                                img.drawHeight = 75
                                img.hAlign = 'LEFT'
                                elements.append(img)
                                elements.append(Spacer(1, 5))

                    elements.append(Spacer(1, 15))

            else:
                # بدون sub_category
                pdf_display = build_display_table(df_cat)

                table_data = [["Test", "Result", "Unit", "Reference Range"]]

                for _, row in pdf_display.iterrows():
                    table_data.append([
                        row["Test"],
                        row["Result"],
                        row["Unit"],
                        row["Reference Range"]
                    ])

                t = Table(
                    table_data,
                    colWidths=[
                        AVAILABLE_WIDTH * 0.35,
                        AVAILABLE_WIDTH * 0.20,
                        AVAILABLE_WIDTH * 0.15,
                        AVAILABLE_WIDTH * 0.30
                    ]
                )

                t.setStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), 'LEFT'),
                    ("VALIGN", (0, 0), (-1, -1), 'MIDDLE'),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ])

                elements.append(t)
                elements.append(Spacer(1, 15))

        # Footnotes
        all_footnotes = df[df["footnote"] != ""]["footnote"].unique()
        if len(all_footnotes) > 0:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("---", styles["Normal"]))
            elements.append(Spacer(1, 5))
            for note in all_footnotes:
                elements.append(Paragraph(f"<i>{note}</i>", styles["Normal"]))
                elements.append(Spacer(1, 3))

        doc.build(elements)
        buffer.seek(0)
        pdf = buffer.read()

        st.download_button(
            label="📄 Download Lab Report",
            data=pdf,
            file_name=f"Report_{patient_name}.pdf",
            mime="application/pdf"
        )
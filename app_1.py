import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import date, timedelta

st.set_page_config(layout="wide")

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

st.title("🏥 Lab Dashboard")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# ✅ تابع ساخت بولت‌چارت
def create_clinical_range_chart(row, pdf_mode=False, width=None):
    ref_low = row["ref_low"]
    ref_high = row["ref_high"]
    val = row["value"]
    
    if pd.isna(val) or not isinstance(val, (int, float)):
        return None
    
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

    fig.add_annotation(
        xref="paper", x=0, y=bar_mid,
        xshift=-(margin_side if pdf_mode else 150) + 10,
        text=f"<b>{row['test_name']}</b><br><span style='font-size:8px'>{row['unit']}</span>",
        showarrow=False, xanchor="left", yanchor="middle",
        font=dict(size=font_size)
    )

    status_color = "green" 
    if row["status"] == "Normal":
        status_color = "green"
    elif row["status"] == "Low":
        status_color = "#FF8C00"
    else:
        status_color = "red"

    fig.add_annotation(
        xref="paper", x=1, y=bar_mid,
        xshift=(margin_side if pdf_mode else 80) - 10,
        text=f"<b>{row['status']}</b>",
        showarrow=False, xanchor="right", yanchor="middle",
        font=dict(size=font_size, color=status_color)
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


if uploaded_file is not None:

    df = pd.read_excel(uploaded_file)
    
    # --- هوشمندسازی ستون‌ها ---
    column_map = {
        'Test': 'test_name', 'Parameter': 'test_name',
        'Result': 'value', 'Value': 'value',
        'Ref Low': 'ref_low', 'Min': 'ref_low',
        'Ref High': 'ref_high', 'Max': 'ref_high',
        'Unit': 'unit'
    }
    df = df.rename(columns=column_map)

    # ✅ تبدیل ستون‌های عددی
    df["ref_low"] = pd.to_numeric(df["ref_low"], errors="coerce")
    df["ref_high"] = pd.to_numeric(df["ref_high"], errors="coerce")

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
    
    # ✅ Patch 2: بروزرسانی تابع get_status
def get_status(row):
    """
    استخراج وضعیت از reference_full_text
    """
    import re
    
    val = row["value"]
    
    # اگر مقدار NaN است
    if pd.isna(val):
        return "Normal"
    
    # اگر مقدار عددی است
    if isinstance(val, (int, float)):
        ref_text = row.get("reference_full_text", "")
        
        # اگر reference_full_text موجود است
        if pd.notnull(ref_text) and str(ref_text).strip() != "":
            ref_text = str(ref_text).strip()
            
            # شکستن متن به خطوط
            lines = [l.strip() for l in ref_text.split('\n') if l.strip()]
            
            # برای هر خط جستجو کن
            for line in lines:
                # استخراج توصیف (قسمت قبل از :)
                description = ""
                if ':' in line:
                    description = line.split(':')[0].strip()
                    line_content = line.split(':', 1)[1].strip()
                else:
                    line_content = line
                
                # استخراج شرط (< > ≤ ≥ - ، به و دیگر)
                # حالت 1: a–b (محدوده بسته)
                range_match = re.search(r'(\d+\.?\d*)\s*[–-]\s*(\d+\.?\d*)', line_content)
                if range_match:
                    low = float(range_match.group(1))
                    high = float(range_match.group(2))
                    
                    if low <= val <= high:
                        return description if description else "Normal"
                
                # حالت 2: <number یا ≤number
                lt_match = re.search(r'[<≤]\s*(\d+\.?\d*)', line_content)
                if lt_match:
                    num = float(lt_match.group(1))
                    if val <= num:
                        return description if description else "Normal"
                
                # حالت 3: >number یا ≥number
                gt_match = re.search(r'[>≥]\s*(\d+\.?\d*)', line_content)
                if gt_match:
                    num = float(gt_match.group(1))
                    if val >= num:
                        return description if description else "Normal"
        
        # اگر در reference_full_text پیدا نشد، از حدود عددی استفاده کن
        low = row.get("ref_low")
        high = row.get("ref_high")
        
        if pd.notnull(low) and val < low:
            return "Low"
        if pd.notnull(high) and val > high:
            return "High"
        return "Normal"
    
    # اگر مقدار متنی است
    val_str = str(val).lower()
    if any(word in val_str for word in ["pos", "reactive", "detected", "present"]):
        return "High"
    if any(word in val_str for word in ["neg", "non", "not detected", "absent"]):
        return "Normal"
    return "Normal"

df["status"] = df.apply(get_status, axis=1)

    # ✅ Summary
    st.subheader("📊 Summary")

    normal_tests = df[df["status"] == "Normal"]["test_name"].tolist()
    high_tests = df[df["status"] == "High"]["test_name"].tolist()
    low_tests = df[df["status"] == "Low"]["test_name"].tolist()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("✅ Normal", len(normal_tests))
        if normal_tests:
            st.caption(", ".join(normal_tests[:3]))

    with col2:
        st.metric("🔺 High", len(high_tests))
        if high_tests:
            st.caption(", ".join(high_tests[:3]))

    with col3:
        st.metric("🔻 Low", len(low_tests))
        if low_tests:
            st.caption(", ".join(low_tests[:3]))

    st.divider()

    categories = df["category"].unique()

    # ✅ نمایش در صفحه (Dashboard)
    for cat in categories:
        df_cat = df[df["category"] == cat]

        display_df = df_cat.copy()

        # ✅ Patch 4: نمایش مقدار با ستاره
        def format_result_with_asterisk(row):
            value_str = str(row["value_clean"])
            
            if row["has_asterisk"]:
                value_str += "*"
            
            if row["status"] == "High":
                return f"🔺 {value_str}"
            elif row["status"] == "Low":
                return f"🔻 {value_str}"
            else:
                return f"{value_str}"

        display_df["value"] = display_df.apply(format_result_with_asterisk, axis=1)
        
        # ✅ Patch 3: استفاده از reference_full_text
        display_df["Reference Range"] = display_df["reference_full_text"].fillna(
            display_df["ref_low"].astype(str) + " - " + display_df["ref_high"].astype(str)
        )
        
        display_df = display_df[["test_name", "value", "unit", "Reference Range"]]
        display_df.columns = ["Test", "Result", "Unit", "Reference Range"]

        def highlight_row(row):
            if "🔺" in row["Result"]:
                return ["background-color: #fdecea"] * len(row)
            elif "🔻" in row["Result"]:
                return ["background-color: #fff7e6"] * len(row)
            else:
                return [""] * len(row)

        styled_df = display_df.style.apply(highlight_row, axis=1)

        # ===== Dashboard (بدون شرط) =====
        st.markdown(f"## 🧪 {cat}")
        
        # بررسی وجود sub_category
        if "sub_category" in df_cat.columns:
            sub_cats = df_cat["sub_category"].dropna().unique()
            has_sub = len(sub_cats) > 0 and not all(s == "" for s in sub_cats)
        else:
            has_sub = False
            sub_cats = []
        
        if has_sub:
            for sub in sub_cats:
                df_sub = df_cat[df_cat["sub_category"] == sub]
                if df_sub.empty:
                    continue
                
                # اگر CBC است، بدون Pie Chart
                if sub == "CBC":
                    st.subheader(f"🔬 {sub}")
                    
                    sub_display = df_sub.copy()
                    sub_display["value"] = sub_display.apply(format_result_with_asterisk, axis=1)
                    sub_display["Reference Range"] = sub_display["reference_full_text"].fillna(
                        sub_display["ref_low"].astype(str) + " - " + sub_display["ref_high"].astype(str)
                    )
                    sub_display = sub_display[["test_name", "value", "unit", "Reference Range"]]
                    sub_display.columns = ["Test", "Result", "Unit", "Reference Range"]
                    styled_sub = sub_display.style.apply(highlight_row, axis=1)
                    
                    col_left, col_right = st.columns([1, 1.2])
                    with col_left:
                        st.dataframe(styled_sub, use_container_width=True, hide_index=True, height=len(df_sub) * 40 + 50)
                    
                    footnotes = df_sub[df_sub["footnote"] != ""]["footnote"].unique()
                    if len(footnotes) > 0:
                        st.caption("---")
                        for note in footnotes:
                            st.caption(f"_{note}_")
                    
                    with col_right:
                        for _, row in df_sub.iterrows():
                            is_numeric_flag = row.get("is_numeric", 1) == 1 if "is_numeric" in row.index else (
                                isinstance(row["value"], (int, float)) and 
                                pd.notnull(row.get("ref_low")) and 
                                pd.notnull(row.get("ref_high"))
                            )
                            if is_numeric_flag:
                                fig = create_clinical_range_chart(row, pdf_mode=False)
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                            else:
                                status_color = "#FF8C00" if row["status"] == "Low" else ("red" if row["status"] == "High" else "green")
                                st.markdown(f'<div style="border-left: 5px solid {status_color}; padding: 10px; margin: 5px; background: #f9f9f9;"><span style="font-weight: bold; font-size: 16px;">{row["test_name"]}:</span> <span style="font-size: 18px; margin-left: 20px;">{row["value_clean"]} {row.get("unit", "")}</span><span style="float: right; color: {status_color}; font-weight: bold;">{row["status"]}</span></div>', unsafe_allow_html=True)
                    st.divider()
                    continue
                
                # برای سایر sub_categories (با Pie Chart)
                st.subheader(f"🔬 {sub}")
                
                sub_display = df_sub.copy()
                sub_display["value"] = sub_display.apply(format_result_with_asterisk, axis=1)
                sub_display["Reference Range"] = sub_display["reference_full_text"].fillna(
                    sub_display["ref_low"].astype(str) + " - " + sub_display["ref_high"].astype(str)
                )
                sub_display = sub_display[["test_name", "value", "unit", "Reference Range"]]
                sub_display.columns = ["Test", "Result", "Unit", "Reference Range"]
                styled_sub = sub_display.style.apply(highlight_row, axis=1)
                
                col_left, col_right = st.columns([1, 1.2])
                with col_left:
                    st.dataframe(styled_sub, use_container_width=True, hide_index=True, height=len(df_sub) * 40 + 50)
                
                footnotes = df_sub[df_sub["footnote"] != ""]["footnote"].unique()
                if len(footnotes) > 0:
                    st.caption("---")
                    for note in footnotes:
                        st.caption(f"_{note}_")
                
                # Pie Chart برای درصدها
                percentage_sub = df_sub[df_sub["unit"] == "%"].copy()
                if not percentage_sub.empty:
                    percentage_numeric = percentage_sub[
                        percentage_sub["value"].notna() & 
                        (percentage_sub["value"] > 0)
                    ].copy()
                    
                    if not percentage_numeric.empty:
                        st.markdown(f"### 📊 {sub} - Distribution")
                        
                        fig_pie = px.pie(
                            percentage_numeric,
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
                        
                        st.plotly_chart(fig_pie, use_container_width=False)
                
                with col_right:
                    for _, row in df_sub.iterrows():
                        if row["unit"] == "%":  # حذف Bullet برای درصدها
                            continue
                        
                        is_numeric_flag = row.get("is_numeric", 1) == 1 if "is_numeric" in row.index else (
                            isinstance(row["value"], (int, float)) and 
                            pd.notnull(row.get("ref_low")) and 
                            pd.notnull(row.get("ref_high"))
                        )
                        if is_numeric_flag:
                            fig = create_clinical_range_chart(row, pdf_mode=False)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        else:
                            status_color = "#FF8C00" if row["status"] == "Low" else ("red" if row["status"] == "High" else "green")
                            st.markdown(f'<div style="border-left: 5px solid {status_color}; padding: 10px; margin: 5px; background: #f9f9f9;"><span style="font-weight: bold; font-size: 16px;">{row["test_name"]}:</span> <span style="font-size: 18px; margin-left: 20px;">{row["value_clean"]} {row.get("unit", "")}</span><span style="float: right; color: {status_color}; font-weight: bold;">{row["status"]}</span></div>', unsafe_allow_html=True)
                st.divider()
        else:
            col_left, col_right = st.columns([1, 1.2])
            with col_left:
                st.dataframe(styled_df, use_container_width=True, hide_index=True, height=len(df_cat) * 40 + 50)
            
            footnotes = df_cat[df_cat["footnote"] != ""]["footnote"].unique()
            if len(footnotes) > 0:
                st.caption("---")
                for note in footnotes:
                    st.caption(f"_{note}_")
            
            percentage_cat = df_cat[df_cat["unit"] == "%"].copy()
            if not percentage_cat.empty:
                percentage_numeric = percentage_cat[
                    percentage_cat["value"].notna() & 
                    (percentage_cat["value"] > 0)
                ].copy()
                
                if not percentage_numeric.empty:
                    st.markdown(f"### 📊 {cat} - Distribution")
                    
                    fig_pie = px.pie(
                        percentage_numeric,
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
                    
                    st.plotly_chart(fig_pie, use_container_width=False)
            
            with col_right:
                for _, row in df_cat.iterrows():
                    if row["unit"] == "%":  # حذف Bullet برای درصدها
                        continue
                    
                    is_numeric_flag = row.get("is_numeric", 1) == 1 if "is_numeric" in row.index else (
                        isinstance(row["value"], (int, float)) and 
                        pd.notnull(row.get("ref_low")) and 
                        pd.notnull(row.get("ref_high"))
                    )
                    if is_numeric_flag:
                        fig = create_clinical_range_chart(row, pdf_mode=False)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    else:
                        status_color = "#FF8C00" if row["status"] == "Low" else ("red" if row["status"] == "High" else "green")
                        st.markdown(f'<div style="border-left: 5px solid {status_color}; padding: 10px; margin: 5px; background: #f9f9f9;"><span style="font-weight: bold; font-size: 16px;">{row["test_name"]}:</span> <span style="font-size: 18px; margin-left: 20px;">{row["value_clean"]} {row.get("unit", "")}</span><span style="float: right; color: {status_color}; font-weight: bold;">{row["status"]}</span></div>', unsafe_allow_html=True)
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

        for cat in categories:
            elements.append(Paragraph(cat, styles["Heading2"]))
            elements.append(Spacer(1, 6))

            df_cat = df[df["category"] == cat]
            
            # بررسی sub_category
            if "sub_category" in df_cat.columns:
                sub_cats = df_cat["sub_category"].dropna().unique()
                has_sub = len(sub_cats) > 0 and not all(s == "" for s in sub_cats)
            else:
                has_sub = False
                sub_cats = []
            
            if has_sub:
                for sub in sub_cats:
                    df_sub = df_cat[df_cat["sub_category"] == sub]
                    if df_sub.empty:
                        continue
                    
                    elements.append(Paragraph(f"  {sub}", styles["Heading3"]))
                    elements.append(Spacer(1, 4))
                    
                    # ===== جدول =====
                    table_data = [["Test", "Result", "Unit", "Reference Range"]]
                    for _, row in df_sub.iterrows():
                        value_display = str(row["value_clean"])
                        if row["has_asterisk"]:
                            value_display += "*"
                        ref_range = row.get("reference_full_text", f"{row['ref_low']} - {row['ref_high']}")
                        table_data.append([row["test_name"], value_display, row["unit"], ref_range])

                    t = Table(
                        table_data,
                        colWidths=[AVAILABLE_WIDTH * 0.35,
                                   AVAILABLE_WIDTH * 0.20,
                                   AVAILABLE_WIDTH * 0.15,
                                   AVAILABLE_WIDTH * 0.30]
                    )
                    t.setStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ALIGN", (0, 0), (-1, -1), 'LEFT'),
                        ("VALIGN", (0, 0), (-1, -1), 'MIDDLE'),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ])
                    t.hAlign = 'LEFT'
                    elements.append(t)
                    elements.append(Spacer(1, 10))
                    
                    # ===== Pie Chart برای درصدها (فقط غیر CBC) =====
                    if sub != "CBC":
                        percentage_sub = df_sub[df_sub["unit"] == "%"].copy()
                        if not percentage_sub.empty:
                            percentage_numeric = percentage_sub[
                                percentage_sub["value"].notna() & 
                                (percentage_sub["value"] > 0)
                            ].copy()
                            
                            if not percentage_numeric.empty:
                                elements.append(Paragraph(f"<b>📊 {sub} - Distribution</b>", styles["Normal"]))
                                elements.append(Spacer(1, 8))
                                
                                fig_pie = px.pie(
                                    percentage_numeric,
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
                                
                                # ✅ تبدیل Pie به عکس و اضافه‌کردن به PDF
                                img_bytes = fig_pie.to_image(format="png", scale=2)
                                img = Image(BytesIO(img_bytes))
                                img.drawWidth = AVAILABLE_WIDTH * 0.7
                                img.drawHeight = 280
                                img.hAlign = 'CENTER'
                                elements.append(img)
                                elements.append(Spacer(1, 10))
                    
                    # ===== Bullet Charts =====
                    for _, row in df_sub.iterrows():
                        if row["unit"] == "%":
                            continue
                        
                        is_numeric_flag = row.get("is_numeric", 1) == 1 if "is_numeric" in row.index else (
                            isinstance(row["value"], (int, float)) and 
                            pd.notnull(row.get("ref_low")) and 
                            pd.notnull(row.get("ref_high"))
                        )
                        if is_numeric_flag:
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
                # ===== بدون sub_category =====
                table_data = [["Test", "Result", "Unit", "Reference Range"]]
                for _, row in df_cat.iterrows():
                    value_display = str(row["value_clean"])
                    if row["has_asterisk"]:
                        value_display += "*"
                    ref_range = row.get("reference_full_text", f"{row['ref_low']} - {row['ref_high']}")
                    table_data.append([row["test_name"], value_display, row["unit"], ref_range])

                t = Table(
                    table_data,
                    colWidths=[AVAILABLE_WIDTH * 0.35,
                               AVAILABLE_WIDTH * 0.20,
                               AVAILABLE_WIDTH * 0.15,
                               AVAILABLE_WIDTH * 0.30]
                )
                t.setStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), 'LEFT'),
                    ("VALIGN", (0, 0), (-1, -1), 'MIDDLE'),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ])
                t.hAlign = 'LEFT'
                elements.append(t)
                elements.append(Spacer(1, 15))
                
                # ===== Pie Chart برای درصدها =====
                percentage_cat = df_cat[df_cat["unit"] == "%"].copy()
                if not percentage_cat.empty:
                    percentage_numeric = percentage_cat[
                        percentage_cat["value"].notna() & 
                        (percentage_cat["value"] > 0)
                    ].copy()
                    
                    if not percentage_numeric.empty:
                        elements.append(Paragraph(f"<b>📊 {cat} - Distribution</b>", styles["Normal"]))
                        elements.append(Spacer(1, 8))
                        
                        fig_pie = px.pie(
                            percentage_numeric,
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
                        
                        # ✅ تبدیل Pie به عکس و اضافه‌کردن به PDF
                        img_bytes = fig_pie.to_image(format="png", scale=2)
                        img = Image(BytesIO(img_bytes))
                        img.drawWidth = AVAILABLE_WIDTH * 0.7
                        img.drawHeight = 280
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 10))
                
                # ===== Bullet Charts =====
                for _, row in df_cat.iterrows():
                    if row["unit"] == "%":
                        continue
                    
                    is_numeric_flag = row.get("is_numeric", 1) == 1 if "is_numeric" in row.index else (
                        isinstance(row["value"], (int, float)) and 
                        pd.notnull(row.get("ref_low")) and 
                        pd.notnull(row.get("ref_high"))
                    )
                    if is_numeric_flag:
                        fig = create_clinical_range_chart(row, pdf_mode=True, width=AVAILABLE_WIDTH * 1.5)
                        if fig:
                            img_bytes = fig.to_image(format="png", scale=2)
                            img = Image(BytesIO(img_bytes))
                            img.drawWidth = AVAILABLE_WIDTH
                            img.drawHeight = 75
                            img.hAlign = 'LEFT'
                            elements.append(img)
                            elements.append(Spacer(1, 5))

            elements.append(Spacer(1, 20))

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
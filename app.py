import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO

st.set_page_config(layout="wide")

# st.markdown("""
# 🏥 Mashhad Pathobiology Lab  
# **Patient Name:** Ali Rezaei  
# **Report Date:** 2024-06-01  
# ---
# """)

mode = st.toggle("📄 Official Report Mode")

if not mode:
    st.title("Lab Dashboard")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

# ✅ تابع ساخت بولت‌چارت (برای صفحه و PDF مشترک)
def create_clinical_range_chart(row, pdf_mode=False, width=None):
    # مقادیر پایه
    ref_low = row["ref_low"]
    ref_high = row["ref_high"]
    val = row["value"]
    diff = ref_high - ref_low
    
    # ✅ اصلاح داینامیک محدوده برای جلوگیری از حذف فلش
    # محدوده پایین: یا 50% کمتر از رفرنس، یا کمتر از مقدار بیمار (اگر بیمار خیلی پایین بود)
    plot_min = min(ref_low - (diff * 0.5), val - (diff * 0.2))
    
    # محدوده بالا: یا 50% بیشتر از رفرنس، یا بیشتر از مقدار بیمار (اگر بیمار خیلی بالا بود)
    plot_max = max(ref_high + (diff * 0.5), val + (diff * 0.2))

    if pdf_mode:
        chart_height = 90
        font_size = 9
        margin_side = 100 
    else:
        chart_height = 110
        font_size = 13
        margin_l, margin_r = 150, 80

    fig = px.scatter()

    # فاصله عمودی نوار تا محور
    bar_y0, bar_y1 = 0.12, 0.32 
    bar_mid = (bar_y0 + bar_y1) / 2

    # رسم نوارهای رنگی (فقط در محدوده رفرنس و حاشیه آن)
    # برای اینکه نوار رنگی تا ابد ادامه پیدا نکند، محدوده‌اش را ثابت نگه می‌داریم
    zone_min = ref_low - (diff * 0.5)
    zone_max = ref_high + (diff * 0.5)

    fig.add_shape(type="rect", x0=zone_min, x1=ref_low, y0=bar_y0, y1=bar_y1, fillcolor="#fdecea", line_width=0)
    fig.add_shape(type="rect", x0=ref_low, x1=ref_high, y0=bar_y0, y1=bar_y1, fillcolor="#6ee7b7", line_width=0)
    fig.add_shape(type="rect", x0=ref_high, x1=zone_max, y0=bar_y0, y1=bar_y1, fillcolor="#fdecea", line_width=0)

    # نام تست در چپ
    fig.add_annotation(
        xref="paper", x=0, y=bar_mid,
        xshift=-(margin_side if pdf_mode else 150) + 10,
        text=f"<b>{row['test_name']}</b><br><span style='font-size:8px'>{row['unit']}</span>",
        showarrow=False, xanchor="left", yanchor="middle",
        font=dict(size=font_size)
    )

    # وضعیت در راست
    status_color = "green" 
    if row["status"] == "Normal":
        status_color = "green"
    elif row["status"] == "Low":
        status_color = "#FF8C00"  # نارنجی تیره (DarkOrange) برای خوانایی بهتر
    else:
        status_color = "red"      # برای وضعیت High

    fig.add_annotation(
        xref="paper", x=1, y=bar_mid,
        xshift=(margin_side if pdf_mode else 80) - 10,
        text=f"<b>{row['status']}</b>",
        showarrow=False, xanchor="right", yanchor="middle",
        font=dict(size=font_size, color=status_color)
    )

    # رفرنس‌ها روی نوار
    for r_val in [ref_low, ref_high]:
        fig.add_annotation(
            x=r_val, y=bar_mid, text=str(r_val),
            showarrow=False, font=dict(size=font_size-2, color="#333")
        )

    # ✅ نشانگر مثلثی (حالا همیشه داخل کادر است)
    fig.add_trace(px.scatter(x=[val], y=[bar_y1 + 0.02]).data[0])
    fig.data[-1].update(marker=dict(size=10, symbol="triangle-down", color="black"))
    
    # عدد مقدار بالای مثلث
    fig.add_annotation(
        x=val, y=bar_y1 + 0.22, text=f"<b>{val}</b>",
        showarrow=False, font=dict(size=font_size)
    )

    fig.update_layout(
        height=chart_height,
        width=width if pdf_mode else None,
        xaxis=dict(
            range=[plot_min, plot_max], # محدوده داینامیک شده
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
    # نقشه‌برداری از نام‌های احتمالی به نام‌های استاندارد ما
    column_map = {
        'Test': 'test_name', 'Parameter': 'test_name',
        'Result': 'value', 'Value': 'value',
        'Ref Low': 'ref_low', 'Min': 'ref_low',
        'Ref High': 'ref_high', 'Max': 'ref_high',
        'Unit': 'unit'
    }
    df = df.rename(columns=column_map)

    # استخراج اطلاعات پایه
    patient_name = df["patient_name"].iloc[0] if 'patient_name' in df.columns else "Unknown"
    raw_date = df["report_date"].iloc[0] if 'report_date' in df.columns else pd.Timestamp.now()
    report_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')
    # تعیین وضعیت (هوشمند برای عدد و متن)
    def get_status(row):
        val = row["value"]
        # اگر مقدار عددی است
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
            val = float(val)
            low = row.get("ref_low")
            high = row.get("ref_high")
            if pd.notnull(low) and val < low: return "Low"
            if pd.notnull(high) and val > high: return "High"
            return "Normal"
        # اگر مقدار متنی است (مثل Positive/Negative)
        else:
            val_str = str(val).lower()
            if any(word in val_str for word in ["pos", "reactive", "detected"]): return "High"
            if any(word in val_str for word in ["neg", "non", "not detected"]): return "Normal"
            return "Normal"

    df["status"] = df.apply(get_status, axis=1)

    # ✅ Summary
    if not mode:
        st.title("Lab Dashboard")
        st.subheader("Summary")

        normal_tests = df[df["status"] == "Normal"]["test_name"].tolist()
        high_tests = df[df["status"] == "High"]["test_name"].tolist()
        low_tests = df[df["status"] == "Low"]["test_name"].tolist()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("✅ Normal", len(normal_tests))
            if normal_tests:
                st.caption(", ".join(normal_tests))

        with col2:
            st.metric("🔺 High", len(high_tests))
            if high_tests:
                st.caption(", ".join(high_tests))

        with col3:
            st.metric("🔻 Low", len(low_tests))
            if low_tests:
                st.caption(", ".join(low_tests))

        st.divider()
    else:
        st.title("📄 Official Report Preview")

    categories = df["category"].unique()

    # ✅ نمایش در صفحه
    for cat in categories:
        df_cat = df[df["category"] == cat]
        
        display_df = df_cat.copy()

        def format_result(row):
            if row["status"] == "High":
                return f"🔺 {row['value']}"
            elif row["status"] == "Low":
                return f"🔻 {row['value']}" # اموجی 🔻 ذاتا قرمز است، اما پس‌زمینه را نارنجی می‌کنیم
            else:
                return f"{row['value']}"

        display_df["value"] = display_df.apply(format_result, axis=1)
        display_df["Reference Range"] = display_df["ref_low"].astype(str) + " - " + display_df["ref_high"].astype(str)
        display_df = display_df[["test_name", "value", "unit", "Reference Range"]]
        display_df.columns = ["Test", "Result", "Unit", "Reference Range"]

        def highlight_row(row):
            if "🔺" in row["Result"]:
                return ["background-color: #fdecea"] * len(row) # تم قرمز برای High
            elif "🔻" in row["Result"]:
                return ["background-color: #fff7e6"] * len(row) # تم نارنجی برای Low
            else:
                return [""] * len(row)

        styled_df = display_df.style.apply(highlight_row, axis=1)

        if not mode:
            st.subheader(f"🧪 {cat}")
            col_left, col_right = st.columns([1, 1.2])

            with col_left:
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

            with col_right:
                for _, row in df_cat.iterrows():
                    fig = create_clinical_range_chart(row, pdf_mode=False)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.divider()
        else:
            # حالت Official
            st.markdown(f"## {cat}")
            st.table(display_df)
            for _, row in df_cat.iterrows():
                fig = create_clinical_range_chart(row, pdf_mode=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown("---")

    # ✅ ساخت PDF
    with st.sidebar:
        st.write("### Export Options")
        buffer = BytesIO()
        # تنظیم حاشیه یکسان برای کل صفحه PDF (مثلاً 50 واحد از چپ و راست)
        PAGE_MARGIN = 50
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=PAGE_MARGIN, 
            leftMargin=PAGE_MARGIN, 
            topMargin=PAGE_MARGIN, 
            bottomMargin=PAGE_MARGIN
        )
        
        # محاسبه عرض مفید صفحه (عرض کل A4 منهای حاشیه‌ها)
        AVAILABLE_WIDTH = A4[0] - 2 * PAGE_MARGIN 
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Mashhad Pathobiology Lab", styles["Heading1"]))
        elements.append(Spacer(1, 8))

        # اطلاعات بیمار
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

            # ✅ ۱. تعریف و مقداردهی table_data قبل از استفاده
            table_data = [["Test", "Result", "Unit", "Reference Range"]]
            for _, row in df_cat.iterrows():
                ref_range = f"{row['ref_low']} - {row['ref_high']}"
                table_data.append([row["test_name"], str(row["value"]), row["unit"], ref_range])

            # ✅ ۲. ساخت جدول
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
            t.hAlign = 'LEFT'  # چپ‌چین کردن جدول
            elements.append(t)
            elements.append(Spacer(1, 15))

            # ✅ ۳. افزودن نمودارهای هر تست
            for _, row in df_cat.iterrows():
                # ایجاد نمودار با عرض کامل و حاشیه‌های یکسان داخلی
                # scale=2 برای کیفیت بالاتر عکس در PDF
                fig = create_clinical_range_chart(row, pdf_mode=True, width=AVAILABLE_WIDTH * 1.5)
                
                img_bytes = fig.to_image(format="png", scale=2)
                img = Image(BytesIO(img_bytes))

                img.drawWidth = AVAILABLE_WIDTH  # هم‌عرض با جدول
                img.drawHeight = 75 # ارتفاع بهینه
                img.hAlign = 'LEFT' # چپ‌چین کردن عکس نمودار

                elements.append(img)
                elements.append(Spacer(1, 5)) # فاصله کم بین نمودارهای یک دسته

            elements.append(Spacer(1, 20)) # فاصله بین دسته‌بندی‌ها

        # نهایی‌سازی فایل
        doc.build(elements)
        buffer.seek(0)
        pdf = buffer.read()

        st.download_button(
            label="📄 Download Official PDF",
            data=pdf,
            file_name=f"Report_{patient_name}.pdf",
            mime="application/pdf"
        )
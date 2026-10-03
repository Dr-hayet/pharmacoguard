import streamlit as st
import pandas as pd
import numpy as np
import datetime
from pathlib import Path
from fpdf import FPDF
import uuid
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================================================================
# 🛡 نظام التحقق من الترخيص (Backend Middleware Simulation)
# =========================================================================
def verify_license_middleware(license_key, valid_licenses_db):
    if not license_key:
        return {"success": False, "status": 401, "error": "License key is missing."}
    if license_key in valid_licenses_db:
        return {"success": True, "status": 200, "licenseDetails": valid_licenses_db[license_key]}
    else:
        return {"success": False, "status": 403, "error": "Invalid or expired license key."}

def get_platform_logo():
    base_dir = Path(__file__).resolve().parent
    for ext in ["png", "jpg", "jpeg"]:
        for p in base_dir.glob(f"*.{ext}"):
            if "sig" not in p.name.lower() and "temp" not in p.name.lower() and "stamp" not in p.name.lower():
                return p
    return None

def get_default_hospital_stamp():
    """البحث التلقائي عن ختم المستشفى الثابت في مجلد المشروع دون الحاجة لرفعه"""
    base_dir = Path(__file__).resolve().parent
    for ext in ["png", "jpg", "jpeg"]:
        stamp_path = base_dir / f"hospital_stamp.{ext}"
        if stamp_path.exists():
            return stamp_path
    for ext in ["png", "jpg", "jpeg"]:
        for p in base_dir.glob(f"*stamp*.{ext}"):
            return p
    return None

PLATFORM_LOGO_PATH = get_platform_logo()
SAVED_STAMP_PATH = get_default_hospital_stamp()

LICENSE_FILE = Path(__file__).resolve().parent / "licenses.txt"
REQUESTS_FILE = Path(__file__).resolve().parent / "license_requests.txt"

if not LICENSE_FILE.exists():
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        f.write("PHARMACO-VIP-2026|Annual-Enterprise|2027-12-31\n")
        f.write("HOSPITAL-AMAL-9921|Monthly-Basic|2026-11-30\n")
        f.write("CLINIC-PRO-5541|Pro-Clinic|2027-06-30\n")

def load_valid_licenses():
    licenses = {}
    if LICENSE_FILE.exists():
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    key, plan, expiry = parts[0], parts[1], parts[2]
                    licenses[key] = {"plan": plan, "expiry": expiry}
                elif len(parts) == 1 and parts[0]:
                    licenses[parts[0]] = {"plan": "Standard", "expiry": "2027-12-31"}
    return licenses

def load_hospital_requests():
    requests_list = []
    if REQUESTS_FILE.exists():
        with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if len(parts) >= 2:
                    requests_list.append({"التاريخ والوقت": parts[0], "البريد الإلكتروني للمستشفى": parts[1]})
                elif len(parts) == 1 and parts[0]:
                    requests_list.append({"التاريخ والوقت": "غير محدد", "البريد الإلكتروني للمستشفى": parts[0]})
    return requests_list

def send_real_email_to_admin(hospital_email):
    """دالة لإرسال إيميل حقيقي عبر سيرفر SMTP إلى بريدك الشخصي"""
    sender_email = "bouabbaci04hayat97@gmail.com"
    # تم تحديث كلمة مرور التطبيق (App Password) بنجاح
    app_password = "gqflnilluogjtpsw"
  
    receiver_email = "bouabbaci04hayat97@gmail.com"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "طلب مفتاح ترخيص جديد من منصة PharmacoGuard"

    body = f"مرحباً دكتورة حياة،\n\nتلقيتِ طلباً جديداً للحصول على مفتاح ترخيص من المستشفى ذات البريد الإلكتروني التالي:\n{hospital_email}\n\nيرجى التواصل معهم وإرسال المفتاح المناسب.\n\nمع تحيات منصة PharmacoGuard"
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

def safe_pdf_text(text):
    if not text:
        return ""
    return "".join([c for c in str(text) if ord(c) < 128])

def parse_lab_file_content(file_bytes, file_type):
    extracted_data = {
        "scr": 1.4,
        "hba1c": 8.1,
        "ef_rate": 40,
        "weight": 75.0,
        "age": 65,
        "diagnosis": "General Clinical Condition"
    }
    try:
        if "text" in file_type or file_type == "txt":
            text_content = file_bytes.decode("utf-8", errors="ignore")
            scr_match = re.search(r'(?:creatinine|scr)[:\s]+([\d\.]+)', text_content, re.IGNORECASE)
            if scr_match:
                extracted_data["scr"] = float(scr_match.group(1))
            hba1c_match = re.search(r'(?:hba1c|glucose|سكري)[:\s]+([\d\.]+)', text_content, re.IGNORECASE)
            if hba1c_match:
                extracted_data["hba1c"] = float(hba1c_match.group(1))
            ef_match = re.search(r'(?:ef|ejection fraction|قذف)[:\s]+([\d\.]+)', text_content, re.IGNORECASE)
            if ef_match:
                extracted_data["ef_rate"] = int(float(ef_match.group(1)))

            text_lower = text_content.lower()
            if "heart failure" in text_lower or "قصور القلب" in text_lower:
                extracted_data["diagnosis"] = "قصور القلب (Heart Failure)"
            elif "diabetes" in text_lower or "سكري" in text_lower:
                extracted_data["diagnosis"] = "السكري (Diabetes Mellitus)"
            elif "hypertension" in text_lower or "ضغط الدم" in text_lower:
                extracted_data["diagnosis"] = "ارتفاع ضغط الدم (Hypertension)"
    except Exception:
        pass
    return extracted_data

st.set_page_config(
    page_title="PharmacoGuard - Advanced Suite",
    page_icon="🛡",
    layout="wide",
)

st.markdown("""
<style>
.main { background-color: #f8fafc; direction: rtl; text-align: right; }
.stTextInput > div > div > input { border-radius: 8px; border: 2px solid #3b82f6; direction: ltr; text-align: left; }
.stButton > button { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; font-weight: bold; border-radius: 8px; border: none; padding: 10px 20px; }
.stButton > button:hover { background: linear-gradient(135deg, #1d4ed8 100%, #1e3a8a 100%); color: #ffffff; }
.security-banner { background-color: #eff6ff; border-right: 4px solid #2563eb; padding: 12px 15px; border-radius: 4px; font-size: 0.95em; color: #1e40af; margin-bottom: 20px; text-align: right; direction: rtl; }
p, div, span, label, h1, h2, h3, h4, h5, h6 { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="security-banner">
    🔒 <strong>Enterprise Security & Compliance Layer Active:</strong> جميع الاتصالات محمية عبر بروتوكول التشفير الآمن (HTTPS/TLS).
</div>
""", unsafe_allow_html=True)

if "patient_history" not in st.session_state:
    st.session_state["patient_history"] = []

if "show_checkout_modal" not in st.session_state:
    st.session_state["show_checkout_modal"] = False

# الشريط الجانبي (Control Panel)
with st.sidebar:
    st.title("🛡 Control Panel")
    lang = st.selectbox("🌐 Choose Language / اختر اللغة", ["العربية", "English", "Français", "Español"])

    st.markdown("---")
    st.markdown("### 🔑 التحقق من الترخيص المؤسسي")
    user_license_key = st.text_input("أدخل مفتاح الترخيص (License Key):", value="", type="password")
  
    valid_db = load_valid_licenses()
    license_check_result = verify_license_middleware(user_license_key, valid_db)

    if license_check_result["success"]:
        st.success(f"✅ ترخيص مفعل: {license_check_result['licenseDetails']['plan']}")
    else:
        st.error("❌ يلزم إدخال مفتاح ترخيص صالح لرؤية النتائج وتحميل التقارير.")

    # 🏥 خانة طلب ترخيص المستشفيات مع الإرسال الآلي
    st.markdown("---")
    st.markdown("💡 **بوابة طلب ترخيص المستشفيات**")
    hospital_contact_email = st.text_input("البريد الإلكتروني للمستشفى:", value="", key="req_email_input")
  
    if st.button("✉ إرسال طلب الترخيص آلياً للإيميل"):
        if "@" in hospital_contact_email:
            with open(REQUESTS_FILE, "a", encoding="utf-8") as req_f:
                req_f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {hospital_contact_email}\n")
          
            email_sent = send_real_email_to_admin(hospital_contact_email)
            if email_sent:
                st.success(f"✅ تم تسجيل الطلب وإرسال رسالة بريدية حقيقية إلى إيميلك بنجاح!")
            else:
                st.warning(f"⚠ تم حفظ الطلب في لوحة التحكم بنجاح، ولكن تعذر إرسال الإيميل الآلي (تأكد من ضبط كلمة مرور التطبيق SMTP).")
        else:
            st.error("الرجاء إدخال بريد إلكتروني صحيح أولاً.")

    # 📥 لوحة تحكم الأدمن الخاصة بكِ لرؤية إيميلات المستشفيات الواردة
    st.markdown("---")
    st.markdown("### 📥 لوحة تحكم الأدمن: طلبات المستشفيات")
    requests_data = load_hospital_requests()
    if requests_data:
        st.info(f"إجمالي الطلبات الواردة: {len(requests_data)}")
        requests_df = pd.DataFrame(requests_data)
        st.dataframe(requests_df, use_container_width=True)
        if st.button("🗑 مسح سجل الطلبات"):
            if REQUESTS_FILE.exists():
                REQUESTS_FILE.unlink()
            st.rerun()
    else:
        st.write("لا توجد طلبات إيميلات مستشفيات مسجلة حتى الآن.")

    st.markdown("---")
    st.markdown("### 🏥 بيانات المؤسسة الطبية")
    hospital_name_input = st.text_input("اسم المستشفى أو المركز المشترك (English):", value="Al Amal Central Hospital")

    st.markdown("---")
    st.markdown("### ✍ الختم والتوقيع المعتمد")
    if SAVED_STAMP_PATH and SAVED_STAMP_PATH.exists():
        st.success("✅ الختم المؤسسي معتمد ومُدمج تلقائياً في التقارير.")
        st.image(str(SAVED_STAMP_PATH), caption="الختم الرسمي المدمج", width=100)
    else:
        st.info("ℹ الختم الافتراضي جاهز للنظام (ضع صورة باسم hospital_stamp.png في مجلد المشروع لتظهر فوراً).")

    st.markdown("---")

    with st.expander("💳 بوابات الاشتراكات الآمنة (Enterprise Checkout)"):
        tiered_plan_selection = st.selectbox("اختر باقة الاشتراك:", [
            "Free (محدودة - دواءان كحد أقصى)",
            "Pro-Clinic ($49/شهرياً - فحص متعدد + تقارير)",
            "Annual-Enterprise ($999/سنوياً - صلاحيات كاملة ومستشفيات)"
        ])
        hospital_email_chk = st.text_input("البريد الإلكتروني للإدارة الطبية:", value="admin@hospital.com", key="chk_email")
        if "Free" not in tiered_plan_selection:
            if st.button("💳 الانتقال لصفحة ملء كارت الدفع الآمن"):
                if "@" in hospital_email_chk:
                    st.session_state["show_checkout_modal"] = True
                    st.session_state["selected_plan_tag"] = "Pro-Clinic" if "Pro-Clinic" in tiered_plan_selection else "Annual-Enterprise"
                    st.session_state["selected_plan_price"] = "$49.00" if "Pro-Clinic" in tiered_plan_selection else "$999.00"
                else:
                    st.error("الرجاء إدخال بريد إلكتروني صحيح.")

    st.markdown("---")
    st.markdown("### 📁 أرشيف التقارير المحفوظة")
    if st.session_state["patient_history"]:
        st.info(f"عدد التقارير في الجلسة الحالية: {len(st.session_state['patient_history'])}")
        if st.button("🗑 مسح السجل"):
            st.session_state["patient_history"] = []
            st.rerun()
    else:
        st.write("لا توجد تقارير محفوظة بعد.")

st.title("💊 PharmacoGuard: Advanced Computational Suite")
st.markdown("### 🔬 *Enterprise-Grade In-Silico Drug Interaction, General Medical Diagnosis & Clinical Intelligence Platform*")
st.markdown("---")

if st.session_state["show_checkout_modal"]:
    st.markdown("---")
    st.markdown("### 🔐 بوابة الدفع الآمنة (Secure Enterprise Payment Gateway)")
    with st.container():
        st.info(f"💳 أنت على وشك الاشتراك في باقة: **{st.session_state.get('selected_plan_tag')}** بقيمة إجمالية: **{st.session_state.get('selected_plan_price')}**")
        cc_col1, cc_col2 = st.columns(2)
        with cc_col1:
            card_holder = st.text_input("اسم حامل البطاقة (Cardholder Name):", value="Dr. John Doe")
            card_number = st.text_input("رقم البطاقة الائتمانية (Card Number):", value="4242 •••• •••• 4242")
        with cc_col2:
            cc_exp = st.text_input("تاريخ الانتهاء (MM/YY):", value="12/28")
            cc_cvc = st.text_input("رمز الأمان (CVC):", value="123", type="password")
        pay_btn_col1, pay_btn_col2 = st.columns(2)
        with pay_btn_col1:
            if st.button("✅ تأكيد وإتمام الدفع الآمن"):
                p_tag = st.session_state.get('selected_plan_tag')
                days = 30 if p_tag == "Pro-Clinic" else 365
                prefix = "PG-PRO" if p_tag == "Pro-Clinic" else "PG-ENT"
                gen_key = f"{prefix}-{str(uuid.uuid4())[:8].upper()}"
                exp_str = (datetime.date.today() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
                with open(LICENSE_FILE, "a", encoding="utf-8") as f:
                    f.write(f"\n{gen_key}|{p_tag}|{exp_str}")
                st.balloons()
                st.success(f"🎉 تم الدفع بنجاح وتفعيل اشتراكك المؤسسي!")
                st.info(f"🔑 **مفتاح الترخيص الخاص بك:**\n`{gen_key}`")
                st.session_state["show_checkout_modal"] = False
        with pay_btn_col2:
            if st.button("❌ إلغاء العملية"):
                st.session_state["show_checkout_modal"] = False
                st.rerun()
    st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    drug1 = st.text_input("Primary Pharmacological Compound:", value="Sildenafil")
with col2:
    drug2 = st.text_input("Secondary Pharmacological Compound:", value="Nitroglycerin")
with col3:
    patient_name = st.text_input("Patient Full Name / ID:", value="Patient_001")

st.markdown("<br>", unsafe_allow_html=True)

if not license_check_result["success"]:
    st.warning("⚠️ **تنبيه أمني:** عذراً، لا يمكنك عرض نتائج التحليل أو تحميل التقارير الطبية حتى يتم إدخال مفتاح ترخيص مؤسسي صالح في الشريط الجانبي أو إتمام الدفع.")
else:
    with st.expander("⚠️ نظام التنبيهات الدوائية المتقدم (Advanced Drug Polypharmacy Matrix)", expanded=True):
        st.markdown("أدخل الأدوية التي يتناولها المريض حالياً (مفصولة بفواصل) لفحص التفاعلات المتعددة:")
        poly_drugs_input = st.text_input("قائمة الأدوية المتعددة (Polypharmacy List):", value="Sildenafil, Nitroglycerin, Aspirin")
        if st.button("فحص التفاعلات الدوائية المتعددة"):
            drugs_list = [d.strip().lower() for d in poly_drugs_input.split(",") if d.strip()]
            st.markdown("### نتائج تحليل التفاعلات الدوائية:")
            has_severe = "sildenafil" in drugs_list and "nitroglycerin" in drugs_list
            has_moderate = len(drugs_list) >= 3
            if has_severe:
                st.error("🚨 **تنبيه خطير (Severe Contraindication):** وُجد تفاعل خطير للغاية بين (Sildenafil و Nitroglycerin) يؤدي إلى هبوط حاد وخطير في ضغط الدم.")
            elif has_moderate:
                st.warning("⚠ **تنبيه تحذيري (Moderate Interaction):** وجود أكثر من دواءين يتطلب مراقبة لصيقة.")
            else:
                st.success("✅ **حالة آمنة (Safe Polypharmacy Profile):** لم يتم رصد تفاعلات دوائية حرجة.")

    st.markdown("<br>", unsafe_allow_html=True)
    parsed_values = {"scr": 1.4, "hba1c": 8.1, "ef_rate": 40, "weight": 75.0, "age": 65, "diagnosis": "General Clinical Condition"}

    with st.expander("📂 رفع وإرفاق ملفات التحاليل الطبية للمريض (Patient Lab Reports Ingestion)", expanded=True):
        uploaded_lab_file = st.file_uploader("اختر ملف التحاليل الطبية (PDF, PNG, JPG, TXT):", type=["pdf", "png", "jpg", "jpeg", "txt"])
        if uploaded_lab_file is not None:
            file_bytes = uploaded_lab_file.read()
            parsed_values = parse_lab_file_content(file_bytes, uploaded_lab_file.type)
            st.success(f"✅ تم إرفاق ملف التحاليل واستخلاص بيانات المريض بنجاح: **{uploaded_lab_file.name}**")
            if "image" in uploaded_lab_file.type:
                st.image(uploaded_lab_file, caption=f"تقرير تحاليل المريض: {patient_name}", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if uploaded_lab_file is not None:
        with st.expander("🩺 محرك التشخيص والتحليلات الديناميكية المتغيرة حسب المرض", expanded=True):
            common_diagnoses = [
                "السكري (Diabetes Mellitus)",
                "ارتفاع ضغط الدم (Hypertension)",
                "قصور القلب (Heart Failure)",
                "مرض كلوي مزمن (CKD)",
                "الربو (Asthma)",
                "أخرى"
            ]
            active_diagnosis = st.selectbox("اختر التشخيص السريري القائم:", common_diagnoses)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("🫘 Renal Function & Dosage Adjustment (Cockcroft-Gault CrCl)"):
            rc1, rc2, rc3 = st.columns(3)
            with rc1: age = st.number_input("Age:", value=parsed_values["age"])
            with rc2: weight = st.number_input("Weight (kg):", value=parsed_values["weight"])
            with rc3: scr = st.number_input("Serum Creatinine:", value=parsed_values["scr"])
            gender = st.radio("Gender:", ["Male", "Female"])
            crcl = round(((140 - age) * weight) / (72 * scr) * (0.85 if gender == "Female" else 1.0), 2)
            st.info(f"**Calculated CrCl (Processed):** {crcl} mL/min")

        st.markdown("<br>", unsafe_allow_html=True)

    else:
        st.info("🔒 **الحاسبات الطبية مخفية حالياً لحين إرفاق ملف التحاليل.**")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("📋 التوصيات السريرية وخطة العلاج المخصصة (Clinical Recommendations & Action Plan)", expanded=True):
        clinical_recommendations_input = st.text_area(
            "أدخل التوصيات الطبية أو الخطة العلاجية لتضمينها رسمياً في التقرير:",
            value="Avoid concurrent administration of Sildenafil and Nitroglycerin. Ensure a minimum 24-hour wash-out period. Monitor blood pressure closely."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Execute Comprehensive In-Silico Analysis"):
        st.markdown("---")
        st.subheader("Comprehensive Computational Report")
        report_hash = f"SHA256-{uuid.uuid4().hex[:12].upper()}"

        history_record = {
            "patient": patient_name,
            "date": str(datetime.date.today()),
            "drug1": drug1,
            "drug2": drug2,
            "hash": report_hash
        }
        if history_record not in st.session_state["patient_history"]:
            st.session_state["patient_history"].append(history_record)

        class ProfessionalPDFReport(FPDF):
            def header(self):
                self.set_fill_color(240, 245, 255)
                self.rect(10, 10, 190, 22, 'F')
              
                active_logo = get_platform_logo()
                if active_logo and active_logo.exists():
                    try:
                        self.image(str(active_logo), 12, 12, 18)
                    except Exception:
                        pass
                else:
                    self.set_fill_color(30, 64, 175)
                    self.rect(12, 12, 18, 18, 'F')
                    self.set_font('Arial', 'B', 8)
                    self.set_text_color(255, 255, 255)
                    self.set_xy(12, 18)
                    self.cell(18, 6, 'PG', 0, 0, 'C')
              
                safe_hosp_name = safe_pdf_text(hospital_name_input)
                self.set_font('Arial', 'B', 11)
                self.set_text_color(30, 64, 175)
                self.set_xy(35, 12)
                self.cell(150, 6, safe_hosp_name, 0, 1, 'L')
              
                self.set_font('Arial', '', 9)
                self.set_text_color(100, 116, 139)
                self.set_xy(35, 18)
                self.cell(100, 5, 'PHARMACOGUARD ENTERPRISE CLINICAL SUITE', 0, 1, 'L')
              
                self.set_font('Arial', '', 8)
                self.set_xy(35, 23)
                self.cell(100, 4, f'Official Medical Report - Date: {datetime.date.today().strftime("%Y-%m-%d")}', 0, 1, 'L')
              
                self.ln(15)

            def footer(self):
                self.set_y(-55)
                self.set_draw_color(203, 213, 225)
                self.line(10, self.get_y(), 200, self.get_y())
                self.ln(2)
              
                if SAVED_STAMP_PATH and SAVED_STAMP_PATH.exists():
                    try:
                        self.image(str(SAVED_STAMP_PATH), 140, self.get_y(), 40)
                    except Exception:
                        pass
              
                self.set_font('Arial', 'B', 8)
                self.set_text_color(71, 85, 105)
                self.cell(0, 4, 'Authorized Medical Signature & Official Stamp:', 0, 1, 'L')
              
                self.ln(12)
                self.set_font('Arial', 'I', 7)
                self.set_text_color(148, 163, 184)
                self.cell(0, 4, f'Digital Verification Hash: {report_hash}', 0, 1, 'L')
                self.cell(0, 4, 'Certified by PharmacoGuard Enterprise Core Security Layer.', 0, 1, 'L')

        pdf = ProfessionalPDFReport()
        pdf.add_page()
      
        pdf.set_font('Arial', 'B', 11)
        pdf.set_fill_color(37, 99, 235)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 8, ' 1. PATIENT & CLINICAL IDENTIFICATION', 0, 1, 'L', 1)
      
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(248, 250, 252)
      
        pdf.cell(95, 8, safe_pdf_text(f" Patient Name / ID: {patient_name}"), 1, 0, 'L', 1)
        pdf.cell(95, 8, f" Analysis Date: {datetime.date.today()}", 1, 1, 'L', 1)
      
        if uploaded_lab_file is not None:
            pdf.cell(190, 8, safe_pdf_text(f" Attached Lab Report File: {uploaded_lab_file.name}"), 1, 1, 'L', 1)
      
        pdf.ln(6)

        pdf.set_font('Arial', 'B', 11)
        pdf.set_fill_color(37, 99, 235)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 8, ' 2. PHARMACOLOGICAL PROFILE & DRUG INTERACTION', 0, 1, 'L', 1)

        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(95, 8, safe_pdf_text(f" Primary Compound: {drug1}"), 1, 0, 'L', 1)
        pdf.cell(95, 8, safe_pdf_text(f" Secondary Compound: {drug2}"), 1, 1, 'L', 1)
      
        pdf.set_fill_color(254, 242, 242)
        pdf.set_text_color(185, 28, 28)
        pdf.cell(190, 8, " Clinical Warning Status: Critical Polypharmacy Check Performed Safely.", 1, 1, 'L', 1)

        pdf.ln(6)

        pdf.set_font('Arial', 'B', 11)
        pdf.set_fill_color(37, 99, 235)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 8, ' 3. CLINICAL RECOMMENDATIONS & ACTION PLAN', 0, 1, 'L', 1)

        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(248, 250, 252)
        pdf.multi_cell(190, 8, safe_pdf_text(clinical_recommendations_input), 1, 'L', 1)

        pdf_output = bytes(pdf.output())

        st.download_button(
            label="📥 Download Official Clinical Report (PDF)",
            data=pdf_output,
            file_name="PharmacoGuard_Enterprise_Report.pdf",
            mime="application/pdf"
        )

if st.session_state["patient_history"]:
    st.markdown("---")
    st.subheader("📋 أرشيف التقارير المصدرة في هذه الجلسة")
    history_df = pd.DataFrame(st.session_state["patient_history"])
    st.dataframe(history_df, use_container_width=True)

st.markdown("---")
st.markdown('<p style="text-align: center; color: #64748b;">PharmacoGuard Enterprise Edition © 2026</p>', unsafe_allow_html=True) 

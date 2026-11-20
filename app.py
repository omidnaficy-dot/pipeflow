"""
PipeFlow — اپ آموزشی Streamlit برای محاسبه افت اصطکاکی لوله (Darcy–Weisbach)
=========================================================================

این فایل فقط رابط کاربری است. تمام محاسبات (رینولدز، ضریب اصطکاک Colebrook/Haaland،
افت هد، ΔP، طول از افت، سرعت از افت) به هسته‌ی آماده‌ی `core.pipe` سپرده می‌شود.
در این فایل هیچ فرمولی دوباره پیاده‌سازی نشده؛ تنها:
  - تبدیل واحد ورودی (mm ↔ m) و (L/s ↔ m³/s)، و
  - قالب‌بندی خروجی انجام می‌شود.

اجرا:
    streamlit run app.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

# --- اطمینان از دسترسی به پکیج core در همان پوشه‌ی پروژه -----------------------
# این کار باعث می‌شود `streamlit run app.py` از هر مسیری کار کند.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# هسته محاسباتی (دست‌نخورده) — فقط import
from core.pipe import (  # noqa: E402
    G,
    RHO,
    NU,
    RE_LAM,
    RE_TURB,
    PipeError,
    head_loss,
    from_flow,
    length_for_head,
    velocity_for_head,
    colebrook,
    haaland,
    friction_factor,
    reynolds,
    regime,
)


# =============================================================================
# ثابت‌ها و جدول‌های کمکی (فقط برای رابط کاربری، نه محاسبات)
# =============================================================================
MATERIALS = {
    "فولاد تجاری (0.045 mm)": 0.045e-3,
    "فولاد ضدزنگ (0.002 mm)": 0.002e-3,
    "چدن (0.26 mm)": 0.26e-3,
    "لوله پلاستیکی PVC (0.0015 mm)": 0.0015e-3,
    "مس کشیده‌شده (0.0015 mm)": 0.0015e-3,
    "بتن صاف (0.3 mm)": 0.3e-3,
    "بتن زبر (3.0 mm)": 3.0e-3,
    "سفاله (1.5 mm)": 1.5e-3,
    "گالوانیزه (0.15 mm)": 0.15e-3,
    "دستی (وارد کردن مقدار)": None,
}

# پیام فارسی برای هر کد خطای PipeError (مطابق E001..E006 در core/pipe.py)
ERROR_MESSAGES = {
    "E001": "قطر لوله (D) باید بزرگتر از صفر باشد.",
    "E002": "طول لوله (L) باید بزرگتر از صفر باشد.",
    "E003": "زبری (ε) نامعتبر است: باید نامنفی و کوچکتر از قطر لوله باشد.",
    "E004": "سرعت (V) یا دبی (Q) باید بزرگتر از صفر باشد.",
    "E005": "خصوصیات سیال (ρ یا ν) باید بزرگتر از صفر باشند.",
    "E006": "حلColebrook همگرا نشد؛ مقدار ورودی را بازبینی کنید.",
}


# =============================================================================
# کمک‌توابع تبدیل واحد و قالب‌بندی (تنها محاسبات مجاز در UI)
# =============================================================================
def to_meter(value: float, unit: str) -> float:
    """تبدیل طول از واحد انتخابی به متر."""
    if unit == "mm":
        return value * 1e-3
    return value  # m


def from_meter(value: float, unit: str) -> float:
    """تبدیل طول از متر به واحد انتخابی (برای نمایش خروجی)."""
    if unit == "mm":
        return value * 1e3
    return value


def fmt(x, digits=4, unit=""):
    """قالب‌بندی عدد با تعداد رقم معنادار؛ مقدار صفر/NaN را هم پوشش می‌دهد."""
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return "—"
        if x == 0:
            s = "0"
        elif abs(x) < 1e-4 or abs(x) >= 1e6:
            s = f"{x:.{digits}e}"
        else:
            s = f"{x:.{digits}g}"
        return f"{s} {unit}".strip()
    except Exception:
        return "—"


def show_pipe_error(e: PipeError):
    """نمایش یکدست و فارسی پیام خطای هسته، بدون stack trace."""
    msg = ERROR_MESSAGES.get(e.code, str(e))
    st.error(f"خطای ورودی ({e.code}): {msg}")


# =============================================================================
# پیکربندی صفحه و RTL
# =============================================================================
st.set_page_config(
    page_title="PipeFlow — محاسبه افت اصطکاکی لوله",
    page_icon="🚰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS: فونت فارسی، راست‌چین، و چینش مناسب اعداد/فرمول‌ها
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Vazirmatn', 'Tahoma', sans-serif;
    }
    .stApp {
        direction: rtl;
    }
    /* راست‌چین کردن ستون‌ها و فرم‌ها در نسخه‌های جدید Streamlit */
    [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
    [data-testid="stMainBlockContainer"] {
        direction: rtl;
    }
    /* جلوگیری از شکستگی اعداد لاتین داخل متن فارسی */
    .stMetric, .stMetricValue, code, pre {
        direction: ltr;
        unicode-bidi: embed;
    }
    h1, h2, h3 { font-weight: 700; }
    .big-title {
        text-align: center;
        padding: 0.6rem 0 0.2rem 0;
    }
    .subtitle {
        text-align: center;
        color: #6b7280;
        margin-bottom: 1rem;
    }
    .katex { direction: ltr; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# نوار کناری: ورودی‌های مشترک (D، L، ε، ρ، ν)
# =============================================================================
with st.sidebar:
    st.markdown("### ⚙️ ورودی‌ها")

    # --- قطر لوله ---
    d_unit = st.radio("واحد قطر لوله D", ["mm", "m"], horizontal=True, index=0,
                      key="d_unit", help="قطر داخلی لوله.")
    D_in = st.number_input(
        f"قطر لوله D ({d_unit})",
        min_value=0.0, value=50.0 if d_unit == "mm" else 0.05,
        format="%.4f", key="D_in",
    )
    D = to_meter(D_in, d_unit)

    # --- طول لوله ---
    l_unit = st.radio("واحد طول L", ["m", "mm"], horizontal=True, index=0, key="l_unit")
    L_in = st.number_input(
        f"طول لوله L ({l_unit})",
        min_value=0.0, value=100.0 if l_unit == "m" else 100000.0,
        format="%.4f", key="L_in",
    )
    L = to_meter(L_in, l_unit)

    # --- زبری مطلق ---
    mat = st.selectbox(
        "جنس لوله (زبری مطلق ε)",
        list(MATERIALS.keys()),
        index=0,
        key="material",
        help="زبری مطلق بر اساس جداول مرجع هیدرولیک انتخاب می‌شود.",
    )
    if MATERIALS[mat] is None:
        eps_unit = st.radio("واحد زبری ε", ["mm", "m"], horizontal=True, index=0, key="eps_unit")
        eps_in = st.number_input(
            f"زبری ε ({eps_unit})",
            min_value=0.0, value=0.045 if eps_unit == "mm" else 0.000045,
            format="%.6f", key="eps_in",
        )
        eps = to_meter(eps_in, eps_unit)
    else:
        eps = MATERIALS[mat]
        st.caption(f"ε = {eps*1e3:.4f} mm")

    # --- خصوصیات سیال ---
    st.markdown("---")
    st.markdown("#### سیال (پیش‌فرض: آب ۲۰°C)")
    use_default = st.checkbox("استفاده از مقادیر پیش‌فرض آب (ρ=1000 kg/m³، ν=1e-6 m²/s)",
                              value=True, key="use_default_fluid")
    if use_default_fluid := use_default:
        rho = RHO
        nu = NU
        st.caption(f"ρ = {rho} kg/m³، ν = {nu:.2e} m²/s")
    else:
        rho = st.number_input("چگالی ρ (kg/m³)", min_value=0.0, value=1000.0,
                              format="%.2f", key="rho_in")
        nu = st.number_input("ویسکوزیته سینماتیک ν (m²/s)", min_value=0.0,
                             value=1.0e-6, format="%.3e", key="nu_in")

    # --- خلاصه زبری نسبی ---
    if D > 0:
        rel = eps / D
        st.markdown("---")
        st.caption(f"زبری نسبی ε/D = {rel:.2e}")


# =============================================================================
# بدنه اصلی: عنوان و تب‌ها
# =============================================================================
st.markdown("<h1 class='big-title'>🚰 PipeFlow</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>محاسبه‌ی آموزشی افت اصطکاکی لوله بر اساس Darcy–Weisbach</p>",
            unsafe_allow_html=True)

tabs = st.tabs(["محاسبه", "فرمول‌ها", "درباره"])


# -----------------------------------------------------------------------------
# تب محاسبه — سه حالت
# -----------------------------------------------------------------------------
with tabs[0]:
    mode = st.radio(
        "حالت محاسبه",
        [
            "الف) محاسبه افت از سرعت یا دبی",
            "ب) محاسبه طول از افت هد مجاز",
            "ج) محاسبه سرعت و دبی از افت هد مشخص",
        ],
        horizontal=False,
        key="mode",
    )

    st.markdown("---")

    # ----- حالت الف: محاسبه افت ---------------------------------------------
    if mode.startswith("الف"):
        input_kind = st.radio("نوع ورودی جریان", ["سرعت V (m/s)", "دبی Q (L/s)"],
                              horizontal=True, key="input_kind")
        if input_kind.startswith("سرعت"):
            V = st.number_input("سرعت V (m/s)", min_value=0.0, value=1.5,
                                format="%.4f", key="V_in")
            Q = None
        else:
            Q_lps = st.number_input("دبی Q (L/s)", min_value=0.0, value=5.0,
                                    format="%.4f", key="Q_in")
            Q = Q_lps * 1e-3  # تبدیل L/s به m³/s
            V = None

        compute = st.button("محاسبه افت", type="primary", key="btn_a")
        if compute:
            try:
                if V is not None:
                    res = head_loss(V, D, L, eps, nu=nu, rho=rho)
                else:
                    res = from_flow(Q, D, L, eps, nu=nu, rho=rho)
                st.session_state["last_result"] = ("loss", res, D, L, eps, nu, rho)
            except PipeError as e:
                show_pipe_error(e)
                st.session_state["last_result"] = None

    # ----- حالت ب: محاسبه طول -----------------------------------------------
    elif mode.startswith("ب"):
        hf = st.number_input("افت هد مجاز hf (m)", min_value=0.0, value=3.0,
                             format="%.4f", key="hf_in_b")
        V = st.number_input("سرعت V (m/s)", min_value=0.0, value=1.2,
                            format="%.4f", key="V_in_b")
        compute = st.button("محاسبه طول موردنیاز", type="primary", key="btn_b")
        if compute:
            try:
                Lreq = length_for_head(hf, V, D, eps, nu=nu)
                # برای نمایش خروجی استاندارد، یک Result کامل هم می‌سازیم
                res = head_loss(V, D, Lreq, eps, nu=nu, rho=rho)
                st.session_state["last_result"] = ("length", (Lreq, res), D, L, eps, nu, rho)
            except PipeError as e:
                show_pipe_error(e)
                st.session_state["last_result"] = None

    # ----- حالت ج: محاسبه سرعت و دبی از افت ---------------------------------
    else:
        hf = st.number_input("افت هد hf (m)", min_value=0.0, value=2.0,
                             format="%.4f", key="hf_in_c")
        compute = st.button("محاسبه سرعت و دبی", type="primary", key="btn_c")
        if compute:
            try:
                V = velocity_for_head(hf, D, L, eps, nu=nu)
                res = head_loss(V, D, L, eps, nu=nu, rho=rho)
                st.session_state["last_result"] = ("velocity", (V, res), D, L, eps, nu, rho)
            except PipeError as e:
                show_pipe_error(e)
                st.session_state["last_result"] = None

    # --- نمایش نتایج ---------------------------------------------------------
    last = st.session_state.get("last_result")
    if last is not None:
        kind = last[0]
        D_d, L_d, eps_d, nu_d, rho_d = last[2], last[3], last[4], last[5], last[6]

        if kind == "loss":
            res = last[1]
            V_out, Re, reg, f_cb, hf_out, dP = res.V, res.Re, res.regime, res.f, res.hf, res.dP
            f_ha = haaland(Re, eps_d / D_d)
            L_used = L_d
        elif kind == "length":
            Lreq, res = last[1]
            V_out, Re, reg, f_cb, hf_out, dP = res.V, res.Re, res.regime, res.f, res.hf, res.dP
            f_ha = haaland(Re, eps_d / D_d)
            L_used = Lreq
        else:  # velocity
            V_out, res = last[1]
            Re, reg, f_cb, hf_out, dP = res.Re, res.regime, res.f, res.hf, res.dP
            f_ha = haaland(Re, eps_d / D_d)
            L_used = L_d

        # نسبت اختلاف Colebrook vs Haaland (صرفاً نمایشی)
        diff_pct = abs(f_cb - f_ha) / f_cb * 100 if f_cb > 0 else 0.0
        Q_out = V_out * math.pi * D_d * D_d / 4  # m³/s (قالب‌بندی بعداً)

        st.markdown("### 📊 نتایج")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("سرعت V", fmt(V_out, 4, "m/s"))
        c1.metric("دبی Q", fmt(Q_out * 1e3, 4, "L/s"))
        c2.metric("عدد رینولدز Re", fmt(Re, 5))
        c2.metric("رژیم جریان", {"laminar": "لامینار",
                                  "transitional": "انتقالی",
                                  "turbulent": "آشفته"}[reg])
        c3.metric("ضریب اصطکاک f (Colebrook)", fmt(f_cb, 6))
        c3.metric("ضریب اصطکاک f (Haaland)", fmt(f_ha, 6))
        c4.metric("اختلاف f", fmt(diff_pct, 3, "%"))
        c4.metric("افت هد hf", fmt(hf_out, 4, "m"))
        c5, c6 = st.columns(2)
        c5.metric("افت فشار ΔP", fmt(dP, 4, "Pa"))
        c6.metric("افت فشار ΔP", fmt(dP / 1e3, 4, "kPa"))

        if kind == "length":
            st.success(f"طول لوله‌ی موردنیاز برای افت هد {hf_out:.4f} m: "
                       f"**{fmt(L_used, 4, 'm')}** "
                       f"(≈ {fmt(from_meter(L_used, 'mm'), 2, 'mm')})")
        elif kind == "velocity":
            st.success(f"برای افت هد {hf_out:.4f} m در طول {L_d:.4f} m: "
                       f"V = **{fmt(V_out, 4, 'm/s')}**، "
                       f"Q = **{fmt(Q_out * 1e3, 4, 'L/s')}**")

        # --- هشدارها ---------------------------------------------------------
        warn_msgs = []
        if RE_LAM <= Re <= RE_TURB:
            warn_msgs.append(
                f"⚠️ جریان در ناحیه‌ی انتقالی است (Re بین {int(RE_LAM)} و {int(RE_TURB)}). "
                "در این ناحیه، رفتار جریان و ضریب اصطکاک با عدم‌قطعیت همراه است و Colebrook "
                "ممکن است دقیق نباشد."
            )
        if D_d > 0 and eps_d / D_d >= 0.05:
            warn_msgs.append(
                "⚠️ زبری نسبی ε/D بسیار بزرگ است (> ۰٫۰۵). زبری از حد عملیاتی فراتر رفته "
                "و معادله Colebrook ممکن است قابل اعتماد نباشد."
            )
        if V_out > 5.0:
            warn_msgs.append(
                f"⚠️ سرعت {fmt(V_out,2,'m/s')} غیرمعمول بالاست؛ "
                "اتلاف انرژی، سایش و خوردگی لوله را بازبینی کنید."
            )
        if V_out < 0.01:
            warn_msgs.append(
                f"⚠️ سرعت {fmt(V_out,4,'m/s')} بسیار پایین است؛ "
                "محاسله‌ها ممکن است به ناحیه‌ی لامینار/خزشی نزدیک باشد."
            )
        if warn_msgs:
            for w in warn_msgs:
                st.warning(w)
        else:
            st.info("✅ هیچ هشدار فعالی برای این نقطه‌ی کارکرد وجود ندارد.")

        # --- نمودار hf(V) با نقطه‌ی جواب فعلی -------------------------------
        st.markdown("### 📈 نمودار افت هد بر حسب سرعت")
        if V_out > 0 and D_d > 0 and L_d > 0:
            # بازه‌ی سرعت اطراف نقطه‌ی جواب؛ بسامد نمونه‌برداری محدود تا سبک بماند.
            v_min = max(V_out * 0.1, 1e-3)
            v_max = max(V_out * 2.0, V_out + 1.0)
            n = 60
            vs = [v_min + (v_max - v_min) * i / (n - 1) for i in range(n)]
            hs = []
            for v in vs:
                try:
                    hs.append(head_loss(v, D_d, L_d, eps_d, nu=nu_d, rho=rho_d).hf)
                except PipeError:
                    hs.append(None)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=vs, y=hs, mode="lines", name="hf(V)",
                line=dict(color="#2563eb", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=[V_out], y=[hf_out], mode="markers",
                name="نقطه‌ی جواب فعلی",
                marker=dict(color="#ef4444", size=12, symbol="star"),
            ))
            fig.update_layout(
                title="افت هد hf بر حسب سرعت V",
                xaxis_title="سرعت V (m/s)",
                yaxis_title="افت هد hf (m)",
                height=420,
                font=dict(family="Vazirmatn, Tahoma, sans-serif", size=13),
                legend=dict(orientation="h", y=-0.2),
                margin=dict(l=40, r=40, t=50, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("نمودار برای مقادیر نامعتبر نمایش داده نمی‌شود.")


# -----------------------------------------------------------------------------
# تب فرمول‌ها
# -----------------------------------------------------------------------------
with tabs[1]:
    st.markdown("## فرمول‌های پایه")
    st.markdown("همه‌ی محاسبات این اپ بر پایه‌ی روابط زیر در هسته‌ی `core/pipe.py` انجام می‌شود.")

    st.markdown("### ۱) عدد رینولدز")
    st.latex(r"Re = \frac{V\,D}{\nu}")
    st.caption("- V سرعت متوسط، D قطر داخلی، ν ویسکوزیته‌ی سینماتیک.")
    st.caption(f"- آستانه‌ها: Re < {int(RE_LAM)} لامینار، Re بین {int(RE_LAM)} و {int(RE_TURB)} "
               f"انتقالی، Re > {int(RE_TURB)} آشفته.")

    st.markdown("### ۲) افت هد اصطکاکی — Darcy–Weisbach")
    st.latex(r"h_f = f\,\frac{L}{D}\,\frac{V^{2}}{2g}")
    st.caption(f"- g = {G} m/s² شتاب گریش؛ f ضریب اصطکاک Darcy.")
    st.latex(r"\Delta P = \rho\, g\, h_f")

    st.markdown("### ۳) ضریب اصطکاک در جریان لامینار")
    st.latex(r"f = \frac{64}{Re}")
    st.caption("تنها برای Re < ۲۳۰۰ به کار می‌رود.")

    st.markdown("### ۴) معادله‌ی Colebrook–White (جریان آشفته)")
    st.latex(
        r"\frac{1}{\sqrt{f}} = -2\,\log_{10}\!\left("
        r"\frac{\varepsilon/D}{3.7} + \frac{2.51}{Re\,\sqrt{f}}"
        r"\right)"
    )
    st.caption("- ε/D زبری نسبی است؛ این معادله ضمنی است و با تکرار حل می‌شود.")

    st.markdown("### ۵) تقریب Haaland (مقایسه)")
    st.latex(
        r"\frac{1}{\sqrt{f}} = -1.8\,\log_{10}\!\left["
        r"\left(\frac{\varepsilon/D}{3.7}\right)^{1.11}"
        r" + \frac{6.9}{Re}"
        r"\right]"
    )
    st.caption("تقریب صریح Colebrook؛ در اپ به‌عنوان مرجع مقایسه‌ای کنار Colebrook نشان داده می‌شود.")

    st.markdown("### ۶) حالت‌های معکوس")
    st.latex(r"L = \frac{h_f\, D\, 2g}{f\, V^{2}} \qquad\text{(طول از افت هد مجاز)}")
    st.latex(r"\text{یافتن } V \text{ از } h_f:\;\; h_f(V) - h_f = 0 \;\;\text{(حل ریشه Brent)}")
    st.caption("حالت (ج) با `scipy.optimize.brentq` در هسته حل می‌شود؛ UI فقط نتیجه را قالب‌بندی می‌کند.")


# -----------------------------------------------------------------------------
# تب درباره
# -----------------------------------------------------------------------------
with tabs[2]:
    st.markdown("## درباره‌ی PipeFlow")
    st.markdown(
        """
**PipeFlow** یک اپ آموزشی است که افت اصطکاکی لوله را بر اساس معادله‌ی
**Darcy–Weisbach** و ضریب اصطکاک **Colebrook** محاسبه می‌کند.

این اپ صرفاً یک رابط کاربری است؛ تمام محاسبات در هسته‌ی مستقل و آزمایش‌شده‌ی
`core/pipe.py` انجام می‌شود که شامل ۱۰ تمرین مرجع در `tests/run_tests.py` است.

**ساختار پروژه:**
```
PipeFlow/
├── app.py            # رابط Streamlit (این فایل)
├── requirements.txt  # وابستگی‌ها
├── README.md         # راهنما و فرض‌ها
├── core/
│   └── pipe.py       # هسته محاسباتی (دست‌نخورده)
└── tests/
    └── run_tests.py  # ۱۰ تمرین مرجع
```

**ویژگی‌ها:**
- سه حالت: محاسبه‌ی افت، طول از افت مجاز، و سرعت/دبی از افت مشخص.
- ورودی با انتخاب واحد (mm/m) و منوی زبری مواد.
- خروجی کامل شامل V، Re، رژیم، f (Colebrook و Haaland با درصد اختلاف)، hf و ΔP.
- نمودار hf(V) با نقطه‌ی جواب فعلی.
- هشدارها برای ناحیه‌ی انتقالی، زبری نسبی بزرگ، و سرعت غیرمعمول.
- تب فرمول‌ها با نمایش LaTeX.

**محدوده‌ی کاربرد:** سیال تراکم‌ناپذیر، لوله‌ی دایره‌ی مقطع، جریان یک‌بعدی پایدار.
        """
    )
    st.markdown("---")
    st.caption("ساخته‌شده برای اهداف آموزشی. برای طراحی صنعتی، استانداردهای مربوطه را اعمال کنید.")

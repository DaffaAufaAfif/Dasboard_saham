import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Price Action Pro", page_icon="📈", layout="centered")

# --- CSS UNTUK MEMPERCANTIK TAMPILAN (HP FRIENDLY) ---
# --- CSS UNTUK MEMPERCANTIK TAMPILAN ---
st.markdown("""
    <style>
    /* Mengatur style kotak Metric */
    .stMetric { 
        background-color: #f0f2f6; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #d6d6d6;
    }
    
    /* MEMAKSA Label (Judul Kecil) menjadi Hitam */
    .stMetric label {
        color: #31333F !important;
    }
    
    /* MEMAKSA Angka Harga (Value) menjadi Biru Gelap/Hitam */
    [data-testid="stMetricValue"] {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI ANALISIS (LOGIKA SAMA DENGAN SEBELUMNYA) ---
def get_analysis(kode_saham, modal_rupiah, risiko_persen):
    # Format Kode
    kode_saham = kode_saham.upper().strip()
    ticker_symbol = f"{kode_saham}.JK" if not kode_saham.endswith(".JK") else kode_saham
    
    try:
        # Download Data
        df = yf.download(ticker_symbol, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df.empty: return None, "Data tidak ditemukan."
        
        # Fix MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Kalkulasi Indikator
        df['MA200'] = df['Close'].rolling(window=200).mean()
        df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()

        # Pivot Points (Data Kemarin)
        prev_high = float(df['High'].iloc[-2])
        prev_low = float(df['Low'].iloc[-2])
        prev_close = float(df['Close'].iloc[-2])
        
        pp = (prev_high + prev_low + prev_close) / 3
        r1 = (2 * pp) - prev_low
        s1 = (2 * pp) - prev_high
        r2 = pp + (prev_high - prev_low)
        s2 = pp - (prev_high - prev_low)
        
        # Data Hari Ini
        current_price = float(df['Close'].iloc[-1])
        ma200_val = float(df['MA200'].iloc[-1])
        last_vol = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Avg_Volume'].iloc[-1])
        
        # Analisis Status
        trend_status = "BULLISH (Uptrend)" if current_price > ma200_val else "BEARISH (Downtrend)"
        vol_status = "TINGGI (Valid)" if last_vol > avg_vol else "NORMAL (Sepi)"
        
        # Trading Plan
        stop_loss = int(s1 * 0.98) # Buffer 2%
        risk_per_share = current_price - stop_loss
        
        # Hindari error jika SL > Harga (jarang terjadi tapi mungkin)
        if risk_per_share <= 0: 
            risk_per_share = 1
            stop_loss = int(current_price * 0.95)
            
        target_profit = int(current_price + (risk_per_share * 2))
        
        # Money Management
        risiko_nominal = modal_rupiah * (risiko_persen / 100)
        max_lot = int((risiko_nominal / risk_per_share) / 100)
        
        return {
            "price": current_price,
            "trend": trend_status,
            "vol": vol_status,
            "pp": pp, "r1": r1, "r2": r2, "s1": s1, "s2": s2,
            "sl": stop_loss,
            "tp": target_profit,
            "max_lot": max_lot,
            "risk_money": risiko_nominal,
            "ticker": ticker_symbol
        }, None

    except Exception as e:
        return None, str(e)

# --- TAMPILAN UI UTAMA (FRONTEND) ---
st.title("📈 Analisis Saham Price Action")
st.caption("Support, Resistance & Money Management Calculator")

# Input User
col1, col2 = st.columns([1, 2])
with col1:
    kode = st.text_input("Kode Saham", value="PGEO", max_chars=4)
with col2:
    modal = st.number_input("Modal Trading (Rp)", value=10000000, step=1000000)

if st.button("ANALISIS SEKARANG 🚀", type="primary"):
    with st.spinner('Sedang mengambil data pasar...'):
        result, error = get_analysis(kode, modal, 2)
        
        if error:
            st.error(f"Terjadi Kesalahan: {error}")
        else:
            # 1. TAMPILAN HARGA UTAMA
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Harga Terakhir", f"Rp {int(result['price'])}")
            
            trend_color = "green" if "BULLISH" in result['trend'] else "red"
            c2.markdown(f"**Tren:** :{trend_color}[{result['trend']}]")
            
            vol_color = "green" if "TINGGI" in result['vol'] else "orange"
            c3.markdown(f"**Volume:** :{vol_color}[{result['vol']}]")

            # 2. TABEL REKOMENDASI (PLAN)
            st.subheader("📋 Rencana Trading")
            
            # Kartu Visual untuk SL dan TP
            p1, p2, p3 = st.columns(3)
            with p1:
                st.info(f"**TARGET (TP)**\n# Rp {result['tp']}")
            with p2:
                st.warning(f"**BELI (Area S1)**\n# Rp {int(result['s1'])}")
            with p3:
                st.error(f"**STOP LOSS**\n# Rp {result['sl']}")
            
            # 3. MONEY MANAGEMENT
            st.success(f"💰 **MAX BELI: {result['max_lot']} LOT** (Resiko Max: Rp {int(result['risk_money']):,})")

            # 4. LEVEL KUNCI LENGKAP
            st.subheader("📍 Level Kunci (Support & Resistance)")
            data_levels = {
                "Level": ["Resistance 2 (R2)", "Resistance 1 (R1)", "PIVOT POINT", "Support 1 (S1)", "Support 2 (S2)"],
                "Harga (Rp)": [int(result['r2']), int(result['r1']), int(result['pp']), int(result['s1']), int(result['s2'])],
                "Keterangan": ["Target Jauh", "Target Dekat", "Garis Tengah", "Area Beli Ideal", "Diskon Besar"]
            }
            df_levels = pd.DataFrame(data_levels)
            st.dataframe(df_levels, hide_index=True, use_container_width=True)

            # Tips
            if result['price'] > result['pp']:
                st.caption("💡 **Tip AI:** Harga di atas Pivot. Momentum positif. Cari koreksi untuk entry.")
            else:
                st.caption("💡 **Tip AI:** Harga di bawah Pivot. Tekanan jual masih ada. Hati-hati false breakout.")

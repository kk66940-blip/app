import pandas as pd
from io import BytesIO
from datetime import datetime

def export_to_excel(df, filename_prefix="Export"):
    """Export DataFrame ke Excel dengan aman menggunakan BytesIO"""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{filename_prefix}_{timestamp}.xlsx"
        
        return output, filename
    except Exception as e:
        raise Exception(f"Gagal export Excel: {str(e)}")

def import_from_excel(uploaded_file, required_columns=None):
    """Import Excel dengan error handling"""
    try:
        df = pd.read_excel(uploaded_file)
        if required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                raise Exception(f"Kolom yang hilang: {missing}")
        return df
    except Exception as e:
        raise Exception(f"Gagal membaca Excel: {str(e)}")
def format_rupiah(value):
    if value is None:
        value = 0
    return f"Rp {float(value):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_rupiah(text):
    if not text:
        return 0.0
    text = text.replace("Rp", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except:
        return 0.0
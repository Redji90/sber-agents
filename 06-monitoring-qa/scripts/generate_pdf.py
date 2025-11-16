from pathlib import Path

from fpdf import FPDF


def main() -> None:
    data_dir = Path("@data")
    data_dir.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()

    sections = [
        (
            "Credit products",
            "Sberbank offers consumer and mortgage loans with a fixed interest rate.",
        ),
        (
            "Loan repayment",
            "Early repayment is free of charge. Customers can choose annuity or differentiated payments.",
        ),
        (
            "Deposits",
            'Popular deposits include "Save" and "Grow". The interest rate depends on the term and amount.',
        ),
        (
            "Insurance",
            "Life insurance is optional and does not affect loan approval, but it can reduce the rate.",
        ),
    ]

    for title, text in sections:
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.multi_cell(0, 10, title)
        pdf.ln(2)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, text)
        pdf.ln(4)

    output_path = data_dir / "sberbank_products.pdf"
    pdf.output(str(output_path))


if __name__ == "__main__":
    main()


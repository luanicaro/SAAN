from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Acessibilidade - SAAN', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        # self.set_fill_color(200, 220, 255)
        self.cell(0, 6, label, 0, 1, 'L', False)
        self.ln(4)

def test():
    try:
        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, u"Aplicação: Teste ção", 0, 1) # Test unicode
        
        pdf_bytes = bytes(pdf.output())
        print(f"Success. Bytes: {len(pdf_bytes)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()

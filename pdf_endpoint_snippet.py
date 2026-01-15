
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
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, body)
        self.ln()

@app.get("/reports/export-pdf")
def export_pdf(applicationId: int, db: Session = Depends(get_db)):
    # 1. Fetch App
    app_obj = db.query(models.Application).filter(models.Application.id == applicationId).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")

    # 2. Calculate Scores (Reusing Logic)
    profiles_data = {k: {"w_sum": 0.0, "w_total": 0.0} for k in NEURODIVERGENCY_PROFILES.keys()}
    profiles_data["Standard"] = {"w_sum": 0.0, "w_total": 0.0}
    
    responses = db.query(models.Response).filter(models.Response.application_id == app_obj.id).all()
    count_resp = len(responses)
    
    for r in responses:
        for ans in r.answers:
            q = ans.question
            raw_score = likert_to_score_0_10(ans.value)
            g_name = q.group.name if q.group else ""
            
            # Standard
            profiles_data["Standard"]["w_sum"] += raw_score
            profiles_data["Standard"]["w_total"] += 1.0
            
            # Profiles
            for p_name in NEURODIVERGENCY_PROFILES.keys():
                w = get_weight_for_group(p_name, g_name)
                profiles_data[p_name]["w_sum"] += raw_score * w
                profiles_data[p_name]["w_total"] += w

    final_scores = {}
    for p_name, data in profiles_data.items():
        if data["w_total"] > 0:
            final_scores[p_name] = round(data["w_sum"] / data["w_total"], 2)
        else:
            final_scores[p_name] = 0.0

    standard_score = final_scores.pop("Standard")

    # 3. Generate PDF
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Title Info
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Aplicação: {app_obj.name}", 0, 1)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.cell(0, 10, f"Total de Avaliações: {count_resp}", 0, 1)
    pdf.ln(10)

    # Main Score
    pdf.set_font('Arial', 'B', 16)
    score_text = f"Nota Geral: {standard_score}/10"
    pdf.cell(0, 10, score_text, 0, 1, 'C')
    pdf.ln(10)

    # Breakdown Table
    pdf.chapter_title("Detalhamento por Neurodivergência")
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 10, 'Neurodivergência', 1)
    pdf.cell(40, 10, 'Nota (0-10)', 1)
    pdf.cell(90, 10, 'Status', 1)
    pdf.ln()

    pdf.set_font('Arial', '', 10)
    for p_name, score in final_scores.items():
        status_txt = "Excelente" if score >= 8 else "Bom" if score >= 5 else "Precisa Melhorar"
        pdf.cell(60, 10, p_name, 1)
        pdf.cell(40, 10, str(score), 1)
        pdf.cell(90, 10, status_txt, 1)
        pdf.ln()
    
    pdf.ln(10)

    # Detailed Info
    pdf.chapter_title("Guias de Acessibilidade")
    
    for p_name, info in NEURO_INFO.items():
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 10, f"{p_name} (Nota: {final_scores.get(p_name, 0)})", 0, 1)
        
        pdf.set_font('Arial', 'I', 10)
        pdf.multi_cell(0, 5, f"Descrição: {info['description']}")
        pdf.ln(2)
        
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, f"Dicas de Acessibilidade: {info['tips']}")
        pdf.ln(5)

    # Output
    pdf_bytes = pdf.output().encode('latin-1')
    buffer = io.BytesIO(pdf_bytes)
    
    headers = {
        'Content-Disposition': f'attachment; filename="report_{app_obj.id}.pdf"'
    }
    return StreamingResponse(buffer, media_type='application/pdf', headers=headers)

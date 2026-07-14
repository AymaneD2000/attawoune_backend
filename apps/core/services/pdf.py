import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from .bulletin import generate_bulletin_pdf

class PDFService:
    @staticmethod
    def generate_report_card(report_card):
        """
        Generate the official bilingual Attawoune bulletin for a ReportCard.
        Returns: BytesIO buffer containing the PDF.
        """
        return generate_bulletin_pdf(report_card)

    @staticmethod
    def generate_financial_statement(statement_data):
        """
        Generate PDF for Financial Statement.
        statement_data: Dict returned by FinancialReportService.generate_statement
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER)
        elements.append(Paragraph("RELEVÉ FINANCIER", title_style))
        elements.append(Spacer(1, 20))
        
        # Student Info
        info_data = [
            ["Nom et Prénom:", statement_data['student']],
            ["Année Académique:", statement_data['academic_year']],
            ["Statut:", statement_data['status']]
        ]
        t = Table(info_data, colWidths=[120, 300])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        
        # Financial Summary
        summary_data = [
            ["Total Dû:", f"{statement_data['total_due']:,.2f} FCFA"],
            ["Total Payé:", f"{statement_data['total_paid']:,.2f} FCFA"],
            ["Reste à Payer:", f"{statement_data['balance']:,.2f} FCFA"]
        ]
        t_sum = Table(summary_data, colWidths=[120, 200])
        t_sum.setStyle(TableStyle([
            ('TEXTCOLOR', (0,2), (1,2), colors.red if statement_data['balance'] > 0 else colors.green),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ]))
        elements.append(t_sum)
        elements.append(Spacer(1, 30))
        
        # Transactions Table
        trans_data = [['Date', 'Référence', 'Mode', 'Montant', 'Statut']]
        for trans in statement_data.get('transactions', []):
            trans_data.append([
                str(trans['date']),
                trans.get('transaction_id') or '-',
                trans.get('payment_method', '-'),
                f"{trans.get('amount', 0):,.0f}",
                trans.get('status', '-')
            ])
            
        t_trans = Table(trans_data, colWidths=[80, 100, 100, 100, 80])
        t_trans.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        elements.append(t_trans)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

class PDFService:
    @staticmethod
    def generate_report_card(report_card):
        """
        Generate PDF for a ReportCard.
        Returns: BytesIO buffer containing the PDF.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            spaceAfter=20
        )
        elements.append(Paragraph("BULLETIN DE NOTES", title_style))
        elements.append(Paragraph(f"Semestre: {report_card.semester.get_semester_type_display()} - {report_card.semester.academic_year.name}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Student Info
        student = report_card.student
        info_data = [
            ["Nom et Prénom:", student.user.get_full_name()],
            ["Matricule:", student.student_id],
            ["Programme:", student.program.name],
            ["Niveau:", str(student.current_level) if student.current_level else "N/A"]
        ]
        t = Table(info_data, colWidths=[100, 300])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        
        # Grades Table
        grades_data = [['Matière', 'Crédits', 'Coeff', 'Note/20', 'Détails', 'Validation']]
        
        # Fetch detailed grades for this student and semester
        from apps.academics.models import Grade
        detailed_grades = Grade.objects.filter(
            student=report_card.student, 
            exam__semester=report_card.semester
        ).select_related('exam')
        
        # Group by course
        grades_by_course = {}
        for g in detailed_grades:
            course_id = g.exam.course_id
            if course_id not in grades_by_course:
                grades_by_course[course_id] = []
            # Format: "Type: Note"
            grades_by_course[course_id].append(f"{g.exam.get_exam_type_display()}: {g.score:.2f}")

        from apps.academics.models import CourseGrade
        course_grades = CourseGrade.objects.filter(
            student=report_card.student,
            semester=report_card.semester
        ).select_related('course')

        for cg in course_grades:
            details = ", ".join(grades_by_course.get(cg.course.id, []))
            grades_data.append([
                cg.course.name,
                str(cg.course.credits),
                str(cg.course.coefficient),
                f"{cg.final_score:.2f}",
                details,
                "Validé" if cg.is_validated else "Non Validé"
            ])
            
        t_grades = Table(grades_data, colWidths=[160, 40, 40, 60, 120, 60])
        t_grades.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 8), # Reduce font size to fit
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_grades)
        elements.append(Spacer(1, 20))
        
        # Summary
        summary_style = ParagraphStyle('Summary', parent=styles['Normal'], alignment=TA_RIGHT)
        elements.append(Paragraph(f"<b>Moyenne Générale: {report_card.gpa:.2f}/20</b>", summary_style))
        elements.append(Paragraph(f"Crédits acquis: {report_card.credits_earned} / {report_card.total_credits}", summary_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

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

import os
import io
import csv
from datetime import datetime, timezone
from typing import Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.app.models.evaluation import EvaluationRun


class EvaluationExporter:
    @staticmethod
    def export_csv(run: EvaluationRun) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["AICTE SmartVerify AI - AI Model Evaluation & Regulatory Scrutiny Metrics"])
        writer.writerow(["Evaluation Run ID", run.id])
        writer.writerow(["Dataset Version", run.dataset_version])
        writer.writerow(["Status", run.status])
        writer.writerow(["Git Commit", run.git_commit or "N/A"])
        writer.writerow(["Overall Accuracy (%)", f"{run.overall_accuracy}%"])
        writer.writerow(["Total Samples", run.total_samples])
        writer.writerow(["Passed Samples", run.passed_samples])
        writer.writerow(["Started At", run.started_at.isoformat() if run.started_at else ""])
        writer.writerow(["Finished At", run.finished_at.isoformat() if run.finished_at else ""])
        writer.writerow(["Duration (seconds)", f"{run.duration_seconds:.2f}s"])
        writer.writerow([])

        metrics = run.metrics_json or {}

        # 1. Classification Metrics
        cls_data = metrics.get("classification", {})
        writer.writerow(["--- CLASSIFICATION METRICS ---"])
        writer.writerow(["Overall Classification Accuracy (%)", cls_data.get("accuracy")])
        writer.writerow(["Macro Precision (%)", cls_data.get("macro_precision")])
        writer.writerow(["Macro Recall (%)", cls_data.get("macro_recall")])
        writer.writerow(["Macro F1 Score (%)", cls_data.get("macro_f1")])
        writer.writerow([])
        writer.writerow(["Document Type", "Precision (%)", "Recall (%)", "F1 Score (%)", "Support (Samples)"])
        for dt_code, stats in cls_data.get("per_type", {}).items():
            writer.writerow([dt_code, stats.get("precision"), stats.get("recall"), stats.get("f1"), stats.get("support")])
        writer.writerow([])

        # 2. Field Extraction Metrics
        field_data = metrics.get("field_extraction", {})
        writer.writerow(["--- FIELD EXTRACTION METRICS ---"])
        writer.writerow(["Overall Exact Match Rate (%)", field_data.get("exact_match_rate")])
        writer.writerow(["Overall Normalized Match Rate (%)", field_data.get("normalized_match_rate")])
        writer.writerow(["Total Fields Evaluated", field_data.get("total_fields_evaluated")])
        writer.writerow([])
        writer.writerow(["Field Name", "Exact Match Rate (%)", "Normalized Match Rate (%)", "Total Evaluated"])
        for f_name, f_stats in field_data.get("per_field", {}).items():
            writer.writerow([f_name, f_stats.get("exact_match_rate"), f_stats.get("normalized_match_rate"), f_stats.get("total")])
        writer.writerow([])

        # 3. Anomaly Detection Metrics
        anom_data = metrics.get("anomaly_detection", {})
        writer.writerow(["--- ANOMALY DETECTOR METRICS ---"])
        writer.writerow(["Overall Precision (%)", anom_data.get("overall_precision")])
        writer.writerow(["Overall Recall (%)", anom_data.get("overall_recall")])
        writer.writerow(["Overall False Positive Rate (FPR %)", anom_data.get("overall_fpr")])
        writer.writerow([])
        writer.writerow(["Detector", "TP", "FP", "TN", "FN", "Precision (%)", "Recall (%)", "FPR (%)"])
        for det_name, d_stats in anom_data.get("per_detector", {}).items():
            writer.writerow([det_name, d_stats.get("tp"), d_stats.get("fp"), d_stats.get("tn"), d_stats.get("fn"), d_stats.get("precision"), d_stats.get("recall"), d_stats.get("fpr")])
        writer.writerow([])

        # 4. OCR & Explainer Grounding
        ocr_data = metrics.get("ocr_performance", {})
        exp_data = metrics.get("explainer_grounding", {})
        writer.writerow(["--- PIPELINE & GROUNDING METRICS ---"])
        writer.writerow(["OCR Success Rate (%)", ocr_data.get("success_rate")])
        writer.writerow(["OCR Avg Processing Time (ms)", ocr_data.get("avg_processing_time_ms")])
        writer.writerow(["Explainer Grounding Rate (%)", exp_data.get("grounding_rate")])
        writer.writerow(["Grounding Statements Checked", exp_data.get("total_statements_checked")])
        writer.writerow([])

        # 5. Failed Cases
        failed_cases = run.failed_cases_json or []
        writer.writerow(["--- FAILED EVALUATION CASES ---"])
        writer.writerow(["File Name", "Document Type", "Error Category", "Expected Value", "Predicted Value", "Failure Reason"])
        for fc in failed_cases:
            writer.writerow([
                fc.get("file"),
                fc.get("document_type"),
                fc.get("error_category"),
                str(fc.get("expected")),
                str(fc.get("got")),
                fc.get("notes"),
            ])

        return output.getvalue()

    @staticmethod
    def export_pdf(run: EvaluationRun, output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=32,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "EvalTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0B3C9D"),
        )
        sub_style = ParagraphStyle(
            "EvalSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        )
        cell_style = ParagraphStyle(
            "EvalCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#1E293B"),
        )
        bold_cell_style = ParagraphStyle(
            "EvalBoldCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#0F2A5C"),
        )
        sec_style = ParagraphStyle(
            "EvalSec",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F2A5C"),
        )

        elements = []

        # Header Title
        elements.append(Paragraph("<b>ALL INDIA COUNCIL FOR TECHNICAL EDUCATION</b>", bold_cell_style))
        elements.append(Paragraph("AICTE SmartVerify AI — AI Pipeline Evaluation Summary", title_style))
        elements.append(Paragraph(
            f"<b>Evaluation Run #{run.id}</b> | Dataset: {run.dataset_version} | Git Commit: {run.git_commit or 'HEAD'} | "
            f"Executed: {run.started_at.strftime('%d-%m-%Y %H:%M:%S UTC') if run.started_at else 'N/A'}",
            sub_style,
        ))
        elements.append(Spacer(1, 6))

        # Honest Disclaimer Banner
        disc_p = Paragraph(
            "<b>HONEST BENCHMARK NOTE:</b> Measured on synthetic data. Real-world accuracy must be validated on actual AICTE submissions. "
            "Governed under <i>'Rules decide, AI explains, Officials approve.'</i>",
            ParagraphStyle("DiscNote", parent=cell_style, fontSize=6.5, leading=8.5, textColor=colors.HexColor("#78350F")),
        )
        disc_table = Table([[disc_p]], colWidths=[524])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F59E0B")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(disc_table)
        elements.append(Spacer(1, 8))

        # Executive Metrics Grid
        metrics = run.metrics_json or {}
        cls_data = metrics.get("classification", {})
        fld_data = metrics.get("field_extraction", {})
        anm_data = metrics.get("anomaly_detection", {})
        ocr_data = metrics.get("ocr_performance", {})
        exp_data = metrics.get("explainer_grounding", {})

        score_cells = [
            [
                Paragraph("<b>Overall Accuracy</b><br/><font size='11' color='#0B3C9D'><b>" + f"{run.overall_accuracy}%</b></font>", bold_cell_style),
                Paragraph("<b>Classification F1</b><br/><font size='11' color='#0B3C9D'><b>" + f"{cls_data.get('macro_f1', 0)}%</b></font>", bold_cell_style),
                Paragraph("<b>Field Match (Norm)</b><br/><font size='11' color='#0B3C9D'><b>" + f"{fld_data.get('normalized_match_rate', 0)}%</b></font>", bold_cell_style),
                Paragraph("<b>Anomaly FPR</b><br/><font size='11' color='#16A34A'><b>" + f"{anm_data.get('overall_fpr', 0)}%</b></font>", bold_cell_style),
                Paragraph("<b>Grounding Rate</b><br/><font size='11' color='#7C3AED'><b>" + f"{exp_data.get('grounding_rate', 0)}%</b></font>", bold_cell_style),
            ]
        ]
        score_table = Table(score_cells, colWidths=[104, 105, 105, 105, 105])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 8))

        # Two-column layout: Top Document Classes & Anomaly Detectors
        elements.append(Paragraph("1. Classification & Anomaly Detection Performance", sec_style))
        per_type = cls_data.get("per_type", {})
        dt_rows = [["Document Type", "Precision", "Recall", "F1", "Samples"]]
        for dt_code, stats in list(per_type.items())[:8]:
            dt_rows.append([
                Paragraph(f"<b>{dt_code}</b>", cell_style),
                f"{stats.get('precision')}%",
                f"{stats.get('recall')}%",
                f"{stats.get('f1')}%",
                str(stats.get('support')),
            ])

        dt_table = Table(dt_rows, colWidths=[140, 80, 80, 80, 50])
        dt_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3C9D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(dt_table)
        elements.append(Spacer(1, 8))

        # Field Extraction Table
        elements.append(Paragraph("2. Field-Level Extraction Accuracy", sec_style))
        per_field = fld_data.get("per_field", {})
        fld_rows = [["Target Field Name", "Exact Match Rate", "Normalized Match Rate", "Evaluated Samples"]]
        for f_name, stats in per_field.items():
            fld_rows.append([
                Paragraph(f"<b>{f_name}</b>", cell_style),
                f"{stats.get('exact_match_rate')}%",
                f"{stats.get('normalized_match_rate')}%",
                str(stats.get('total')),
            ])
        fld_table = Table(fld_rows, colWidths=[170, 118, 118, 118])
        fld_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2A5C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(fld_table)
        elements.append(Spacer(1, 8))

        # Failed Cases Sample (if any)
        failed_cases = run.failed_cases_json or []
        if failed_cases:
            elements.append(Paragraph(f"3. Failure Scrutiny Log ({len(failed_cases)} exceptions noted)", sec_style))
            fail_rows = [["File", "Category", "Expected", "Actual Outcome"]]
            for fc in failed_cases[:4]:
                fail_rows.append([
                    Paragraph(f"<b>{fc.get('file', '')}</b>", cell_style),
                    Paragraph(fc.get("error_category", ""), cell_style),
                    Paragraph(str(fc.get("expected", ""))[:25], cell_style),
                    Paragraph(str(fc.get("got", ""))[:25], cell_style),
                ])
            fail_table = Table(fail_rows, colWidths=[120, 100, 150, 154])
            fail_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(fail_table)

        doc.build(elements)


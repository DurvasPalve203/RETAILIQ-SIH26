from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
except Exception:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'reportlab'])
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

out_path = Path(__file__).resolve().parent / 'RetailIQ_Project_Review.pdf'

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleBold', parent=styles['Title'], fontSize=20, leading=24, textColor=colors.HexColor('#0f172a'), spaceAfter=14))
styles.add(ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#111827'), spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle(name='Body', parent=styles['BodyText'], fontSize=10.5, leading=15, textColor=colors.HexColor('#1f2937')))
styles.add(ParagraphStyle(name='BoldBody', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=10.5, leading=15, textColor=colors.HexColor('#111827')))

story = []
story.append(Paragraph('RetailIQ Project Review & Production Gap Analysis', styles['TitleBold']))
story.append(Paragraph('Prepared for SIH-style evaluation of live camera readiness and production gaps.', styles['Body']))
story.append(Spacer(1, 0.2 * inch))

sections = [
    ('1. Executive Summary', 'The current system has a strong front-end structure and modular AI architecture, but it is still built around synthetic/demo logic rather than a strict live-camera data pipeline. The biggest issue is that demo data is seeded at startup, synthetic fallback is treated as an operational mode, and synthetic ground-truth boxes override real detection results. As a result, the dashboard appears live while the underlying metrics are still simulation-driven.'),
    ('2. Where the project is going wrong', 'The root problem is visible in the code path: startup seeds demo data in backend/main.py and demo_seed.py; the video capture layer falls back to synthetic mode when the source is blank or invalid; and the detection layer explicitly trusts synthetic_meta["ground_truth_boxes"] before running real person/product detection. This means the system can remain in demo mode even when a camera is connected or intended to be live.'),
    ('3. Critical findings from the code review', '• Startup seeding inserts demo shelves, SKUs, queue history, and stock events every time the backend boots.\n• Camera source normalization treats None, demo, mock, and synthetic as synthetic.\n• Detector logic uses synthetic ground-truth boxes instead of real detections when they exist.\n• SyntheticShelfStream generates fake people, products, shelf depletion, and queue behavior.\n• Frontend logic reads these states without strict validation that the camera is currently producing fresh real frames.'),
    ('4. Why the live mobile IP camera still looks demo-driven', 'The system is not fail-closed around missing or invalid camera data. If the mobile stream is blank, disconnected, or blocked, the system can still revert to fallback mode. Because the synthetic stream emits fake detection metadata and the detector trusts it, the dashboard continues to show realistic numbers even though they are not derived from real camera evidence. That is the core reason your project still behaves like a demo despite webcam integration.'),
    ('5. Production readiness gaps', '• Demo seeding must be removed from the production startup path.\n• Synthetic mode must be an explicit opt-in demo mode, not a fallback default.\n• Stream validation must require fresh frames before using live data.\n• Real detections must be used for all production inference.\n• Privacy blur must be mandatory on public dashboard output.\n• Zone calibration must be user-defined and live, not hard-coded from seeded demo data.'),
    ('6. Recommended architecture for production', 'The correct production flow is: camera input → source validation → frame freshness checks → real detection → person tracking → zone occupancy → queue analysis → event generation → prediction → alert prioritization → dashboard action feed → response verification. Synthetic data should exist only in a separate demo sandbox, not in the real operational pipeline.'),
    ('7. Priority fix order', '1. Remove startup seeding from production mode.\n2. Force explicit live-source selection and fail closed on invalid camera sources.\n3. Disable synthetic ground-truth injection outside demo mode.\n4. Add stream health and freshness checks.\n5. Enforce privacy blur on public dashboard streams.\n6. Build dashboard and alerts around live event streams, not seeded or synthetic values.'),
    ('8. Final conclusion', 'The project already has impressive concepts, modular architecture, and polished dashboard design. The main problem is not the idea; it is that the runtime path still favors simulation over real camera truth. For SIH evaluation, the system must visibly prove that the camera produces real detections, real shelf occupancy changes, real queue growth, and real alerts. Without that, it reads as a strong demo prototype rather than a production-ready edge AI system.'),
]

for title, text in sections:
    story.append(Paragraph(title, styles['Heading2']))
    story.append(Paragraph(text, styles['Body']))
    story.append(Spacer(1, 0.12 * inch))

story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph('Key recommendation: live camera truth must be the only source of operational data in production. Demo mode should be isolated, explicit, and clearly labeled.', styles['BoldBody']))

doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=0.7*inch, rightMargin=0.7*inch, topMargin=0.7*inch, bottomMargin=0.7*inch)
doc.build(story)
print(f'PDF created: {out_path}')

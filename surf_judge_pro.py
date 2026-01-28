from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import json
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import csv

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Store heat data in memory
current_heat = {
    'metadata': {
        'heat_number': '',
        'round': '',
        'location': '',
        'duration': 20,  # minutes
        'start_time': None,
        'is_closed': False,
        'notes': ''
    },
    'surfers': [
        {'color': 'Red', 'waves': [None] * 12, 'interference': 0},  # 0 = none, 1 = second wave, 2 = first wave
        {'color': 'Blue', 'waves': [None] * 12, 'interference': 0},
        {'color': 'Yellow', 'waves': [None] * 12, 'interference': 0},
        {'color': 'Green', 'waves': [None] * 12, 'interference': 0},
        {'color': 'White', 'waves': [None] * 12, 'interference': 0}
    ],
    'priority_order': []  # Empty = no priority established yet
}

def calculate_rankings():
    """Calculate live rankings for all surfers with proper tiebreaker logic"""
    results = []
    
    for idx, surfer in enumerate(current_heat['surfers']):
        valid_waves = [w for w in surfer['waves'] if w is not None]
        valid_waves.sort(reverse=True)
        top_two = valid_waves[:2] if len(valid_waves) >= 2 else valid_waves
        
        # Apply interference penalty
        # interference: 0 = none, 1 = half of second wave, 2 = half of first wave
        total = sum(top_two)
        if surfer['interference'] == 1 and len(top_two) >= 2:
            # INT-2: Deduct half of second best wave
            total -= (top_two[1] / 2)
        elif surfer['interference'] == 2 and len(top_two) >= 1:
            # INT-1: Deduct half of best wave
            total -= (top_two[0] / 2)
        
        results.append({
            'idx': idx,
            'color': surfer['color'],
            'top_waves': top_two,
            'all_waves_sorted': valid_waves,  # All waves sorted for tiebreaker
            'total': total,
            'all_waves': [w for w in surfer['waves'] if w is not None],
            'interference': surfer['interference']
        })
    
    # Sort with proper tiebreaker logic:
    # 1. By total (descending)
    # 2. If tied on total, by highest single wave (descending)
    # 3. If still tied, by 3rd wave, 4th wave, etc.
    def sort_key(result):
        # Create tuple: (total, wave1, wave2, wave3, ...)
        # Pad with 0s if fewer waves to ensure proper comparison
        waves = result['all_waves_sorted'] + [0] * (12 - len(result['all_waves_sorted']))
        return (result['total'],) + tuple(waves)
    
    results.sort(key=sort_key, reverse=True)
    
    # Add position
    for pos, result in enumerate(results, 1):
        result['position'] = pos
    
    return results

@app.route('/')
def index():
    surfers_with_idx = [(idx, surfer) for idx, surfer in enumerate(current_heat['surfers'])]
    return render_template('index.html', 
                         surfers=surfers_with_idx,
                         metadata=current_heat['metadata'])

@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    data = request.json
    current_heat['metadata'].update(data)
    return jsonify({'success': True})

@app.route('/start_timer', methods=['POST'])
def start_timer():
    current_heat['metadata']['start_time'] = datetime.now().isoformat()
    return jsonify({'success': True, 'start_time': current_heat['metadata']['start_time']})

@app.route('/update_score', methods=['POST'])
def update_score():
    data = request.json
    surfer_idx = data['surfer_idx']
    wave_idx = data['wave_idx']
    score = data['score']
    
    if score == '':
        current_heat['surfers'][surfer_idx]['waves'][wave_idx] = None
    else:
        try:
            score_val = float(score)
            if 0 <= score_val <= 10:
                current_heat['surfers'][surfer_idx]['waves'][wave_idx] = score_val
            else:
                return jsonify({'error': 'Score must be between 0 and 10'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid score'}), 400
    
    # Return live rankings
    rankings = calculate_rankings()
    return jsonify({'success': True, 'rankings': rankings})

@app.route('/toggle_priority', methods=['POST'])
def toggle_priority():
    data = request.json
    surfer_idx = data['surfer_idx']
    
    # Remove surfer from current position if they're in the order
    current_priority_order = current_heat['priority_order']
    if surfer_idx in current_priority_order:
        current_priority_order.remove(surfer_idx)
    
    # Add to end (lowest priority)
    current_priority_order.append(surfer_idx)
    
    # Build response with updated priority order
    # Include surfers NOT in priority_order as "tied"
    all_surfers = set(range(5))
    surfers_in_order = set(current_priority_order)
    tied_surfers = all_surfers - surfers_in_order
    
    priority_display = []
    
    # Show tied surfers first
    if tied_surfers:
        for idx in sorted(tied_surfers):
            priority_display.append({
                'position': 'TIED',
                'color': current_heat['surfers'][idx]['color'],
                'idx': idx
            })
    
    # Then show ordered surfers
    for position, idx in enumerate(current_priority_order, len(tied_surfers) + 1):
        priority_display.append({
            'position': position,
            'color': current_heat['surfers'][idx]['color'],
            'idx': idx
        })
    
    return jsonify({'success': True, 'priority_order': priority_display})

@app.route('/toggle_interference', methods=['POST'])
def toggle_interference():
    data = request.json
    surfer_idx = data['surfer_idx']
    
    # Cycle through: 0 -> 1 -> 2 -> 0
    current_heat['surfers'][surfer_idx]['interference'] = (current_heat['surfers'][surfer_idx]['interference'] + 1) % 3
    
    rankings = calculate_rankings()
    return jsonify({'success': True, 
                   'interference': current_heat['surfers'][surfer_idx]['interference'],
                   'rankings': rankings})

@app.route('/get_rankings', methods=['GET'])
def get_rankings():
    rankings = calculate_rankings()
    return jsonify({'rankings': rankings})

@app.route('/get_priority_order', methods=['GET'])
def get_priority_order():
    all_surfers = set(range(5))
    surfers_in_order = set(current_heat['priority_order'])
    tied_surfers = all_surfers - surfers_in_order
    
    priority_display = []
    
    if tied_surfers:
        for idx in sorted(tied_surfers):
            priority_display.append({
                'position': 'TIED',
                'color': current_heat['surfers'][idx]['color'],
                'idx': idx
            })
    
    for position, idx in enumerate(current_heat['priority_order'], len(tied_surfers) + 1):
        priority_display.append({
            'position': position,
            'color': current_heat['surfers'][idx]['color'],
            'idx': idx
        })
    
    return jsonify({'priority_order': priority_display})

@app.route('/close_heat', methods=['POST'])
def close_heat():
    current_heat['metadata']['is_closed'] = True
    results = calculate_rankings()
    return jsonify({'results': results})

@app.route('/reopen_heat', methods=['POST'])
def reopen_heat():
    current_heat['metadata']['is_closed'] = False
    return jsonify({'success': True})

@app.route('/reset_heat', methods=['POST'])
def reset_heat():
    for surfer in current_heat['surfers']:
        surfer['waves'] = [None] * 12
        surfer['interference'] = 0
    current_heat['metadata']['start_time'] = None
    current_heat['metadata']['is_closed'] = False
    current_heat['metadata']['notes'] = ''
    current_heat['priority_order'] = []  # Reset to no priority
    return jsonify({'success': True})

@app.route('/export_csv', methods=['GET'])
def export_csv():
    results = calculate_rankings()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Metadata header
    writer.writerow(['Heat Number', current_heat['metadata']['heat_number']])
    writer.writerow(['Round', current_heat['metadata']['round']])
    writer.writerow(['Location', current_heat['metadata']['location']])
    writer.writerow(['Duration', f"{current_heat['metadata']['duration']} minutes"])
    if current_heat['metadata']['notes']:
        writer.writerow(['Notes', current_heat['metadata']['notes']])
    writer.writerow([])  # Empty row
    
    # Full scoring grid
    writer.writerow(['FULL SCORING GRID'])
    grid_header = ['Surfer'] + [f'W{i+1}' for i in range(12)]
    writer.writerow(grid_header)
    
    for surfer in current_heat['surfers']:
        row = [surfer['color']]
        for wave in surfer['waves']:
            row.append(f"{wave:.2f}" if wave is not None else '-')
        writer.writerow(row)
    
    writer.writerow([])  # Empty row
    
    # Final results
    writer.writerow(['FINAL RESULTS'])
    writer.writerow(['Position', 'Surfer', 'Best Wave', '2nd Wave', 'Total', 'Interference'])
    
    # Data
    for result in results:
        waves = result['top_waves'] + [None] * (2 - len(result['top_waves']))
        interference_label = 'INT-2' if result['interference'] == 1 else 'INT-1' if result['interference'] == 2 else 'None'
        writer.writerow([
            result['position'],
            result['color'],
            f"{waves[0]:.2f}" if waves[0] is not None else '-',
            f"{waves[1]:.2f}" if waves[1] is not None else '-',
            f"{result['total']:.2f}",
            interference_label
        ])
    
    # Prepare file for download
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"heat_{current_heat['metadata']['heat_number']}_results.csv"
    )

@app.route('/export_pdf', methods=['GET'])
def export_pdf():
    results = calculate_rankings()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f"<b>Heat Results - {current_heat['metadata']['round']}</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Metadata
    meta_text = f"Heat: {current_heat['metadata']['heat_number']} | Location: {current_heat['metadata']['location']} | Duration: {current_heat['metadata']['duration']} min"
    meta = Paragraph(meta_text, styles['Normal'])
    elements.append(meta)
    elements.append(Spacer(1, 12))
    
    # Notes if present
    if current_heat['metadata']['notes']:
        notes_text = f"<b>Notes:</b> {current_heat['metadata']['notes']}"
        notes = Paragraph(notes_text, styles['Normal'])
        elements.append(notes)
        elements.append(Spacer(1, 20))
    else:
        elements.append(Spacer(1, 8))
    
    # Full scoring grid
    grid_title = Paragraph("<b>Full Scoring Grid</b>", styles['Heading2'])
    elements.append(grid_title)
    elements.append(Spacer(1, 8))
    
    grid_data = [['Surfer'] + [f'W{i+1}' for i in range(12)]]
    for surfer in current_heat['surfers']:
        row = [surfer['color']]
        for wave in surfer['waves']:
            row.append(f"{wave:.1f}" if wave is not None else '-')
        grid_data.append(row)
    
    grid_table = Table(grid_data)
    grid_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(grid_table)
    elements.append(Spacer(1, 20))
    
    # Final results section
    results_title = Paragraph("<b>Final Results</b>", styles['Heading2'])
    elements.append(results_title)
    elements.append(Spacer(1, 8))
    
    # Results table
    data = [['Position', 'Surfer', 'Best Wave', '2nd Wave', 'Total', 'Interference']]
    
    for result in results:
        waves = result['top_waves'] + [None] * (2 - len(result['top_waves']))
        interference_label = 'INT-2' if result['interference'] == 1 else 'INT-1' if result['interference'] == 2 else 'None'
        data.append([
            str(result['position']),
            result['color'],
            f"{waves[0]:.2f}" if waves[0] is not None else '-',
            f"{waves[1]:.2f}" if waves[1] is not None else '-',
            f"{result['total']:.2f}",
            interference_label
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"heat_{current_heat['metadata']['heat_number']}_results.pdf"
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

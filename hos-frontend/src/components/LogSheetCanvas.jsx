import { useEffect, useRef } from 'react';

function LogSheetCanvas({ log }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !log?.log_sheet_data) return;

    const ctx = canvas.getContext('2d');
    const width = 1380;
    const height = 1120;
    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#111827';
    ctx.lineWidth = 1;

    const fitText = (text, maxWidth, font = '13px Arial') => {
      const safe = String(text || '');
      ctx.font = font;
      if (ctx.measureText(safe).width <= maxWidth) return safe;
      let out = safe;
      while (out.length > 0 && ctx.measureText(`${out}...`).width > maxWidth) {
        out = out.slice(0, -1);
      }
      return `${out}...`;
    };

    const drawBox = ({ x, y, w, h, label, value, font = '13px Arial' }) => {
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(x + 1, y + 1, w - 2, 14);
      ctx.font = '10px Arial';
      ctx.fillStyle = '#475569';
      ctx.fillText(label, x + 6, y + 11);
      ctx.font = font;
      ctx.fillStyle = '#0f172a';
      ctx.fillText(fitText(value, w - 12, font), x + 6, y + h - 9);
    };

    const drawWrappedText = ({ text, x, y, maxWidth, lineHeight, maxLines, font = '12px Arial' }) => {
      ctx.font = font;
      ctx.fillStyle = '#111827';
      const words = String(text || '').split(/\s+/);
      const lines = [];
      let line = '';
      words.forEach((word) => {
        const candidate = line ? `${line} ${word}` : word;
        if (ctx.measureText(candidate).width <= maxWidth) {
          line = candidate;
        } else {
          if (line) lines.push(line);
          line = word;
        }
      });
      if (line) lines.push(line);
      const renderLines = lines.slice(0, maxLines);
      renderLines.forEach((lineText, index) => {
        const textToDraw =
          index === maxLines - 1 && lines.length > maxLines
            ? fitText(lineText, maxWidth, font)
            : lineText;
        ctx.fillText(textToDraw, x, y + index * lineHeight);
      });
    };

    // Header
    ctx.font = 'bold 44px Arial';
    ctx.fillStyle = '#111827';
    ctx.fillText('Drivers Daily Log', 48, 62);
    ctx.font = '16px Arial';
    ctx.fillStyle = '#334155';
    ctx.fillText('(24 hours)', 50, 86);

    // Top fields
    const boxY = 102;
    const sheet = log.log_sheet_data;
    drawBox({
      x: 48,
      y: boxY,
      w: 430,
      h: 44,
      label: 'From',
      value: sheet.from_location || '',
    });
    drawBox({
      x: 492,
      y: boxY,
      w: 430,
      h: 44,
      label: 'To',
      value: sheet.to_location || '',
    });
    drawBox({
      x: 936,
      y: boxY,
      w: 396,
      h: 44,
      label: 'Date (MM/DD/YYYY)',
      value: `${sheet.month}/${sheet.day}/${sheet.year}`,
    });

    const detailY = 176;
    drawBox({ x: 48, y: detailY, w: 340, h: 40, label: 'Driver Name', value: sheet.driver_name || 'N/A' });
    drawBox({ x: 400, y: detailY, w: 220, h: 40, label: 'Co-Driver', value: sheet.co_driver_name || 'N/A' });
    drawBox({ x: 632, y: detailY, w: 330, h: 40, label: 'Carrier', value: sheet.carrier_name || 'N/A' });
    drawBox({ x: 974, y: detailY, w: 358, h: 40, label: 'Main Office', value: sheet.main_office_address || 'N/A' });

    drawBox({
      x: 48,
      y: detailY + 52,
      w: 560,
      h: 40,
      label: 'Truck / Trailer Numbers',
      value: `${sheet.truck_or_tractor_numbers || 'N/A'} / ${sheet.trailer_numbers || 'N/A'}`,
    });
    drawBox({
      x: 620,
      y: detailY + 52,
      w: 712,
      h: 40,
      label: 'Shipping Document / Commodity',
      value: `${sheet.shipping_document_number || 'N/A'} / ${sheet.shipper_and_commodity || 'N/A'}`,
    });

    // Main graph box
    const labelGutterX = 48;
    const labelGutterW = 240;
    const gridX = labelGutterX + labelGutterW;
    const gridY = 270;
    const gridW = 1044;
    const gridH = 320;
    ctx.strokeRect(labelGutterX, gridY, labelGutterW + gridW, gridH);
    ctx.beginPath();
    ctx.moveTo(gridX, gridY);
    ctx.lineTo(gridX, gridY + gridH);
    ctx.strokeStyle = '#94a3b8';
    ctx.stroke();
    ctx.strokeRect(gridX, gridY, gridW, gridH);

    const rowTop = gridY + 38;
    ctx.font = '11px Arial';
    for (let i = 0; i <= 24; i += 1) {
      const x = gridX + (i / 24) * gridW;
      ctx.beginPath();
      ctx.moveTo(x, rowTop - 14);
      ctx.lineTo(x, gridY + gridH);
      ctx.strokeStyle = i % 6 === 0 ? '#6b7280' : '#e5e7eb';
      ctx.stroke();
      if (i < 24) {
        for (let quarter = 1; quarter <= 3; quarter += 1) {
          const qx = x + (quarter * gridW) / (24 * 4);
          ctx.beginPath();
          ctx.moveTo(qx, rowTop - 4);
          ctx.lineTo(qx, gridY + gridH);
          ctx.strokeStyle = '#f3f4f6';
          ctx.stroke();
        }
      }
      if (i < 24) {
        const label = i === 0 ? 'Mid' : i === 12 ? 'Noon' : `${i}`;
        ctx.fillStyle = '#111827';
        ctx.fillText(label, x + 3, rowTop - 19);
      }
    }

    const rows = [
      { key: 'OFF_DUTY', label: '1. Off Duty' },
      { key: 'SLEEPER', label: '2. Sleeper Berth' },
      { key: 'DRIVING', label: '3. Driving' },
      { key: 'ON_DUTY_NOT_DRIVING', label: '4. On Duty (Not Driving)' },
    ];
    const rowHeight = 70;
    rows.forEach((row, idx) => {
      const y = rowTop + idx * rowHeight;
      ctx.strokeStyle = '#9ca3af';
      ctx.beginPath();
      ctx.moveTo(labelGutterX, y);
      ctx.lineTo(gridX + gridW, y);
      ctx.stroke();
      ctx.fillStyle = '#111827';
      ctx.font = '13px Arial';
      ctx.fillText(fitText(row.label, labelGutterW - 20, '13px Arial'), labelGutterX + 10, y + 24);
    });

    const rowYMap = {
      OFF_DUTY: rowTop + 28,
      SLEEPER: rowTop + rowHeight + 28,
      DRIVING: rowTop + rowHeight * 2 + 28,
      ON_DUTY_NOT_DRIVING: rowTop + rowHeight * 3 + 28,
    };
    ctx.strokeStyle = '#111827';
    ctx.lineWidth = 4;
    const segments = [...(sheet.segments || [])].sort((a, b) => a.start_hour - b.start_hour);
    let previous = null;
    segments.forEach((segment) => {
      const y = rowYMap[segment.status] || rowYMap.ON_DUTY_NOT_DRIVING;
      const x1 = gridX + (segment.start_hour / 24) * gridW;
      const x2 = gridX + (segment.end_hour / 24) * gridW;

      if (previous) {
        const tx = x1;
        ctx.beginPath();
        ctx.moveTo(previous.endX, previous.y);
        ctx.lineTo(tx, previous.y);
        ctx.stroke();

        if (previous.y !== y) {
          ctx.beginPath();
          ctx.moveTo(tx, previous.y);
          ctx.lineTo(tx, y);
          ctx.stroke();
        }
      }

      ctx.beginPath();
      ctx.moveTo(x1, y);
      ctx.lineTo(Math.max(x2, x1 + 1), y);
      ctx.stroke();
      previous = { endX: Math.max(x2, x1 + 1), y };
    });

    const totals = sheet.status_totals || {};
    ctx.font = '16px Arial';
    ctx.fillStyle = '#111827';
    const summaryX = 48;
    const summaryStartY = 632;
    const summaryLine = 24;
    const summaryItems = [
      `Off Duty: ${totals.off_duty_hours ?? 0}h`,
      `Sleeper: ${totals.sleeper_hours ?? 0}h`,
      `Driving: ${totals.driving_hours ?? 0}h`,
      `On Duty ND: ${totals.on_duty_not_driving_hours ?? 0}h`,
      `Total: ${log.total_hours}h`,
    ];
    summaryItems.forEach((item, index) => {
      ctx.fillText(item, summaryX, summaryStartY + index * summaryLine);
    });

    ctx.font = '15px Arial';
    const metaStartY = summaryStartY + summaryItems.length * summaryLine + 14;
    const metaLine = 22;
    const metaItems = [
      `Cycle used at start: ${sheet.cycle_used_hours_start}h`,
      `Miles driving today: ${sheet.total_miles_driving_today ?? 0}`,
      fitText(`Driver signature: ${sheet.driver_signature || 'N/A'}`, 760, '15px Arial'),
    ];
    metaItems.forEach((item, index) => {
      ctx.fillText(item, summaryX, metaStartY + index * metaLine);
    });

    const remarksY = metaStartY + metaItems.length * metaLine + 14;
    ctx.strokeStyle = '#334155';
    ctx.strokeRect(48, remarksY, 1284, 220);
    ctx.font = 'bold 18px Arial';
    ctx.fillStyle = '#111827';
    ctx.fillText('Remarks', 56, remarksY - 10);
    drawWrappedText({
      text: sheet.remarks_text || '',
      x: 58,
      y: remarksY + 28,
      maxWidth: 1260,
      lineHeight: 24,
      maxLines: 8,
      font: '15px Arial',
    });
  }, [log]);

  const downloadCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `daily-log-${log.date}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <>
      <canvas ref={canvasRef} className="log-preview" />
      <button type="button" className="download-link" onClick={downloadCanvas}>
        Download Log Image
      </button>
    </>
  );
}

export default LogSheetCanvas;

"""inspect_ui.py — static HTML page for GET /inspect-ui.

A single-page form that lets a user kick off the full ADK inspection
pipeline (POST /adk-pipeline) and links to the resulting report once
it's ready.
"""

from __future__ import annotations

INSPECT_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>InspectIQ — Generate Report</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: #F2F4F7;
      color: #1A1A1A;
      line-height: 1.6;
    }

    /* ── Header ── */
    .header {
      background: #0D2340;
      color: white;
      padding: 20px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .logo { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
    .logo-accent { color: #4DA6FF; }
    .logo-sub { font-size: 12px; color: #7AABDF; margin-top: 3px; letter-spacing: 0.3px; }
    .header-right {
      text-align: right;
      font-size: 13px;
      color: #7AABDF;
      line-height: 1.5;
    }
    .header-right strong { color: #C8DEFF; font-size: 14px; display: block; }

    /* ── Container ── */
    .container { max-width: 640px; margin: 0 auto; padding: 40px 24px 64px; }

    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: #0D2340;
      margin-bottom: 6px;
    }
    .page-subtitle {
      font-size: 14px;
      color: #7A8599;
      margin-bottom: 24px;
    }

    /* ── Form card ── */
    .card {
      background: white;
      border-radius: 10px;
      padding: 28px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }

    .field { margin-bottom: 18px; }
    .field label {
      display: block;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #7A8599;
      margin-bottom: 6px;
    }
    .field input,
    .field select {
      width: 100%;
      padding: 10px 12px;
      font-size: 14px;
      font-family: inherit;
      color: #1A1A1A;
      border: 1px solid #D8DEE8;
      border-radius: 6px;
      background: #FAFBFC;
    }
    .field input:focus,
    .field select:focus {
      outline: none;
      border-color: #4DA6FF;
      background: white;
    }

    .submit-btn {
      width: 100%;
      padding: 13px;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.3px;
      color: white;
      background: #0D2340;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s ease;
    }
    .submit-btn:hover { background: #163A66; }
    .submit-btn:disabled {
      background: #B0B7C3;
      cursor: not-allowed;
    }

    /* ── Status area ── */
    .status-block {
      margin-top: 20px;
      display: none;
    }
    .status-block.visible { display: block; }

    .status-row {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #EEF3FA;
      border-radius: 8px;
      padding: 14px 16px;
      border-left: 5px solid #0D2340;
    }
    .status-text {
      font-size: 13.5px;
      color: #2A2A2A;
    }
    .status-text strong { color: #0D2340; }

    /* Spinner */
    .spinner {
      width: 20px;
      height: 20px;
      border: 3px solid #C8DEFF;
      border-top-color: #0D2340;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      flex-shrink: 0;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Result */
    .result-row {
      background: #ECFDF5;
      border-left: 5px solid #1A7A4A;
      border-radius: 8px;
      padding: 16px;
      font-size: 14px;
    }
    .result-row a {
      color: #0D2340;
      font-weight: 700;
      text-decoration: none;
      border-bottom: 2px solid #4DA6FF;
    }
    .result-row a:hover { color: #163A66; }

    /* Error */
    .error-row {
      background: #FDECEA;
      border-left: 5px solid #CC0000;
      border-radius: 8px;
      padding: 16px;
      font-size: 13.5px;
      color: #B91C1C;
    }

    .footer {
      text-align: center;
      font-size: 12px;
      color: #AAA;
      margin-top: 32px;
      line-height: 1.7;
    }

    @media (max-width: 600px) {
      .header { flex-direction: column; gap: 12px; text-align: center; padding: 16px 20px; }
      .header-right { text-align: center; }
    }
  </style>
</head>
<body>

<div class="header">
  <div>
    <div class="logo">Inspect<span class="logo-accent">IQ</span></div>
    <div class="logo-sub">Powered by MCAG Technologies</div>
  </div>
  <div class="header-right">
    <strong>Florida Home Inspection Report</strong>
    AI-Powered Report Generator
  </div>
</div>

<div class="container">
  <div class="page-title">Generate Inspection Report</div>
  <div class="page-subtitle">
    Submit a single inspection photo and property details. The AI pipeline
    classifies the photo, validates it against Florida regulations, drafts
    the narrative, and audits the result &mdash; usually in about 60 seconds.
  </div>

  <div class="card">
    <form id="inspect-form">
      <div class="field">
        <label for="photo_url">Photo URL</label>
        <input type="url" id="photo_url" name="photo_url" placeholder="https://example.com/roof.jpg" required>
      </div>

      <div class="field">
        <label for="property_address">Property Address</label>
        <input type="text" id="property_address" name="property_address" placeholder="123 Main St, Tampa, FL 33601" required>
      </div>

      <div class="field">
        <label for="inspection_date">Inspection Date</label>
        <input type="date" id="inspection_date" name="inspection_date" required>
      </div>

      <div class="field">
        <label for="inspection_type">Inspection Type</label>
        <select id="inspection_type" name="inspection_type">
          <option value="4-point">4-Point</option>
          <option value="wind-mit">Wind Mitigation</option>
          <option value="full">Full Inspection</option>
        </select>
      </div>

      <button type="submit" class="submit-btn" id="submit-btn">Generate Report</button>
    </form>

    <div class="status-block" id="status-block">
      <div class="status-row" id="status-row">
        <div class="spinner" id="spinner"></div>
        <div class="status-text" id="status-text">
          Running the inspection pipeline &mdash; this can take up to a minute&hellip;
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    InspectIQ Agent &mdash; AI-assisted reporting system by MCAG Technologies.<br>
    AI-generated reports require review by a licensed inspector before use.
  </div>
</div>

<script>
  const form = document.getElementById('inspect-form');
  const submitBtn = document.getElementById('submit-btn');
  const statusBlock = document.getElementById('status-block');
  const statusRow = document.getElementById('status-row');

  // Default the date field to today.
  document.getElementById('inspection_date').valueAsDate = new Date();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const photoUrl = document.getElementById('photo_url').value.trim();
    const propertyAddress = document.getElementById('property_address').value.trim();
    const inspectionDate = document.getElementById('inspection_date').value;
    const inspectionType = document.getElementById('inspection_type').value;

    submitBtn.disabled = true;
    statusBlock.classList.add('visible');
    statusRow.className = 'status-row';
    statusRow.innerHTML = `
      <div class="spinner"></div>
      <div class="status-text">Running the inspection pipeline &mdash; this can take up to a minute&hellip;</div>
    `;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 150000);

    try {
      const resp = await fetch('/adk-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: '',
          photo_url: photoUrl,
          property_address: propertyAddress,
          inspection_date: inspectionDate,
          inspection_type: inspectionType,
        }),
        signal: controller.signal,
      });

      const data = await resp.json();

      if (resp.status === 429) {
        startRateLimitCountdown();
        return;
      }

      if (!resp.ok) {
        let detail = data.detail || `Request failed (HTTP ${resp.status})`;
        if (Array.isArray(detail)) {
          detail = detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
        } else if (typeof detail === 'object') {
          detail = JSON.stringify(detail);
        }
        throw new Error(detail);
      }

      const reportUrl = `/report/${data.report_id}`;
      statusRow.className = 'result-row';
      statusRow.innerHTML = `
        Report generated successfully.
        <a href="${reportUrl}" target="_blank">View Report &rarr;</a>
      `;
      submitBtn.disabled = false;
    } catch (err) {
      if (err.name === 'AbortError') {
        statusRow.className = 'error-row';
        statusRow.textContent = 'Request timed out. Please try again.';
      } else {
        statusRow.className = 'error-row';
        statusRow.textContent = `Error: ${err.message || err.detail || JSON.stringify(err)}`;
      }
      submitBtn.disabled = false;
    } finally {
      clearTimeout(timeoutId);
    }
  });

  function startRateLimitCountdown() {
    let secondsLeft = 60;
    statusRow.className = 'error-row';
    statusRow.textContent = `Rate limit reached — please wait ${secondsLeft} seconds and try again.`;

    const interval = setInterval(() => {
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        clearInterval(interval);
        statusBlock.classList.remove('visible');
        submitBtn.disabled = false;
        return;
      }
      statusRow.textContent = `Rate limit reached — please wait ${secondsLeft} seconds and try again.`;
    }, 1000);
  }
</script>

</body>
</html>"""

/* Native ES-module React: no JSX compiler, CDN, build server or chart dependency. */
import { number, signed, dateLabel, timeLabel, linePath, query, shiftDate } from './utils.js';
const { createElement: h, useState, useEffect, useRef } = window.React;
const C = (tag, props, ...children) => h(tag, props, ...children.flat(Infinity));
const icons = {
  wind: ['M3 8h12a3 3 0 1 0-3-3', 'M3 12h18', 'M3 16h10a3 3 0 1 1-3 3'],
  grid: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M3 14h7v7H3z', 'M14 14h7v7h-7z'],
  chart: ['M4 3v17h17', 'm7 14 4-5 4 3 5-7'],
  shield: ['M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7z', 'm8 12 3 3 5-6'],
  arrow: ['M5 12h14', 'm13 6 6 6-6 6'],
  download: ['M12 3v12', 'm7 10 5 5 5-5', 'M4 17v4h16v-4'],
  clock: ['M12 8v5l4 2', 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'],
  info: ['M12 11v6', 'M12 7h.01', 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'],
  code: ['m8 5-6 7 6 7', 'm16 5 6 7-6 7', 'm14 3-4 18']
};
function Icon({ name, size = 20 }) {
  return C(
    'svg',
    {
      viewBox: '0 0 24 24',
      width: size,
      height: size,
      fill: 'none',
      stroke: 'currentColor',
      strokeWidth: 1.6,
      strokeLinecap: 'round',
      strokeLinejoin: 'round',
      'aria-hidden': true
    },
    (icons[name] || icons.info).map((d, i) => C('path', { d, key: i }))
  );
}
function useApi(path, params) {
  const qs = query(params), requestKey = `${path}?${qs}`;
  const [state, set] = useState({ key: null, data: null, error: null, loading: true });
  useEffect(() => {
    const controller = new AbortController();
    set({ key: requestKey, data: null, error: null, loading: true });
    fetch(requestKey, { signal: controller.signal }).then(async (r) => {
      const body = await r.json();
      if (!r.ok)
        throw Error(typeof body.detail === 'string' ? body.detail : 'The request could not be completed. Check the dates and cutoff.');
      return body;
    }).then(data => set({ key: requestKey, data, error: null, loading: false })).catch(e => {
      if (e.name !== 'AbortError')
        set({ key: requestKey, data: null, error: e.message, loading: false });
    });
    return () => controller.abort();
  }, [requestKey]);
  // Do not render a snapshot response as an accuracy response during tab changes.
  return state.key === requestKey ? state : { data: null, error: null, loading: true };
}
function Badge({ children, tone = '' }) { return C('span', { className: `badge ${tone}` }, children); }
function Stat({ label, value, unit, detail, tone = '' }) {
  return C(
    'article',
    { className: `stat ${tone}` },
    C('div', { className: 'stat-label' }, label),
    C('div', { className: 'stat-value' }, value, C('span', null, unit)),
    C('div', { className: 'stat-detail' }, detail)
  );
}
function Panel({ title, subtitle, action, children, className = '' }) {
  return C(
    'section',
    { className: `panel ${className}` },
    C(
      'div',
      { className: 'panel-head' },
      C('div', null, C('h2', null, title), subtitle && C('p', null, subtitle)),
      action
    ),
    children
  );
}
function Empty({ error, onDemo }) {
  return C(
    'div',
    { className: 'empty-state', role: 'status' },
    C('div', { className: 'empty-icon' }, C(Icon, { name: 'wind', size: 34 })),
    C('span', { className: 'eyebrow' }, 'REAL DATA REQUIRED'),
    C('h2', null, 'Your decision desk is ready.'),
    C('p', null, error || 'No verified Elexon snapshot has been installed.'),
    C('pre', null, 'python -m backend.app.ingest'),
    C(
      'p',
      { className: 'small' },
      'Run the importer on a network-connected machine, then restart the app. There is no automatic fallback to invented data.'
    ),
    C(
      'button',
      { className: 'primary', onClick: onDemo },
      'Explore the synthetic sandbox',
      C(Icon, { name: 'arrow', size: 17 })
    ),
    C('span', { className: 'small' }, 'Clearly labelled test data. Not January 2026 results.')
  );
}
function Loading() {
  return C(
    'div',
    { className: 'loading', role: 'status' },
    C('span', { className: 'spinner' }),
    'Loading the decision-time snapshot…'
  );
}
function LineChart({ points, reveal, showBand }) {
  const [hover, setHover] = useState(null);
  const width = 880, height = 300, left = 60, right = 22, top = 28, bottom = 40;
  const vals = points.flatMap(p => [p.forecast_mw, reveal ? p.actual_mw : null, showBand ? p.range_low_mw : null, showBand ? p.range_high_mw : null]).filter(v => v != null);
  const lo = Math.min(0, ...vals), hi = Math.max(2000, Math.ceil(Math.max(...vals, 0) / 2000) * 2000);
  const x = i => left + i / (points.length - 1) * (width - left - right), y = v => top + (hi - v) / (hi - lo) * (height - top - bottom);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + (hi - lo) * i / 4);
  let regions = [], run = [];
  points.forEach((p, i) => {
    if (showBand && p.range_low_mw != null) {
      run.push({ p, i });
    }
    else if (run.length) {
      regions.push(run);
      run = [];
    }
  });
  if (run.length)
    regions.push(run);
  return C(
    'div',
    { className: 'chart-wrap' },
    C(
      'div',
      { className: 'legend' },
      C('span', null, C('i', { className: 'legend-line forecast' }), 'Decision-time forecast'),
      reveal && C('span', null, C('i', { className: 'legend-line actual' }), 'Outturn · hindsight'),
      showBand && C('span', null, C('i', { className: 'legend-box' }), 'Prior-only empirical range')
    ),
    C(
      'svg',
      {
        viewBox: `0 0 ${width} ${height}`,
        className: 'line-chart',
        role: 'img',
        'aria-label': 'Wind power by delivery half-hour in megawatts. Exact data are available in the interval table.',
        onMouseLeave: () => setHover(null)
      },
      C('text', { x: left, y: 14, className: 'axis-unit' }, 'MW'),
      ticks.map((v, i) => C(
        'g',
        { key: i },
        C('line', { x1: left, x2: width - right, y1: y(v), y2: y(v), className: 'gridline' }),
        C('text', { x: left - 12, y: y(v) + 4, textAnchor: 'end', className: 'axis-text' }, number(v))
      )),
      [0, 8, 16, 24, 32, 40, 47].map(i => C(
        'text',
        { key: i, x: x(i), y: height - 13, textAnchor: 'middle', className: 'axis-text' },
        timeLabel(points[i]?.start_time)
      )),
      regions.map((r, j) => C(
        'path',
        {
          key: j,
          d: r.map(({ p, i }, k) => `${k ? 'L' : 'M'}${x(i)},${y(p.range_low_mw)}`).join(' ') + r.slice().reverse().map(({ p, i }) => `L${x(i)},${y(p.range_high_mw)}`).join(' ') + 'Z',
          className: 'range-area'
        }
      )),
      C('path', { d: linePath(points, 'forecast_mw', x, y), className: 'series forecast' }),
      reveal && C('path', { d: linePath(points, 'actual_mw', x, y), className: 'series actual' }),
      points.map((p, i) => p.forecast_mw != null && C('circle', { key: i, cx: x(i), cy: y(p.forecast_mw), r: 2, className: 'forecast-dot' })),
      points.map((p, i) => C(
        'rect',
        {
          key: `hit${i}`,
          x: x(i) - 8,
          y: top,
          width: 16,
          height: height - top - bottom,
          fill: 'transparent',
          onMouseEnter: () => setHover(i)
        }
      )),
      hover != null && C(
        'g',
        null,
        C('line', { x1: x(hover), x2: x(hover), y1: top, y2: height - bottom, className: 'hover-line' }),
        points[hover].forecast_mw != null && C('circle', { cx: x(hover), cy: y(points[hover].forecast_mw), r: 5, className: 'hover-dot' })
      )
    ),
    C(
      'div',
      { className: 'chart-footer' },
      hover != null ? C(
        'span',
        null,
        C('strong', null, `${timeLabel(points[hover].start_time)} GMT`),
        '  ·  Forecast ',
        number(points[hover].forecast_mw),
        ' MW',
        reveal ? `  ·  Actual ${number(points[hover].actual_mw)} MW` : '',
        `  ·  Published ${dateLabel(points[hover].publish_time, { day: 'numeric', month: 'short' })} ${timeLabel(points[hover].publish_time)}`
      ) : C('span', null, 'Hover to inspect a half-hour. Missing values remain gaps.'),
      C('span', null, 'Delivery time · Europe/London')
    )
  );
}
function IntervalTable({ points, reveal }) {
  const [expanded, setExpanded] = useState(false); return C(
    Panel,
    {
      title: 'The numbers behind the curve',
      subtitle: 'Exact target-time alignment. Every selected forecast retains its publication time.',
      action: C(
        'button',
        { className: 'text-button', onClick: () => setExpanded(!expanded) },
        expanded ? 'Show fewer' : `All ${points.length} intervals`
      )
    },
    C(
      'div',
      { className: 'table-scroll' },
      C(
        'table',
        null,
        C(
          'thead',
          null,
          C(
            'tr',
            null,
            ['Delivery GMT', 'Forecast MW', 'Published GMT', 'Age at cutoff', 'Revision MW', ...(reveal ? ['Actual MW', 'Error MW'] : [])].map(s => C('th', { key: s }, s))
          )
        ),
        C(
          'tbody',
          null,
          (expanded ? points : points.slice(0, 8)).map(p => C(
            'tr',
            { key: p.start_time },
            C('td', { className: 'mono' }, timeLabel(p.start_time)),
            C('td', { className: 'numeric' }, number(p.forecast_mw)),
            C(
              'td',
              null,
              p.publish_time ? `${dateLabel(p.publish_time, { day: 'numeric', month: 'short' })}, ${timeLabel(p.publish_time)}` : 'Unavailable'
            ),
            C('td', null, p.age_hours == null ? '—' : `${number(p.age_hours, 1)}h`),
            C('td', { className: 'numeric' }, signed(p.revision_mw)),
            reveal && C('td', { className: 'numeric' }, number(p.actual_mw)),
            reveal && C('td', { className: p.error_mw > 0 ? 'numeric amber-text' : 'numeric' }, signed(p.error_mw))
          ))
        )
      )
    )
  );
}
function Decision({ data, reveal, setReveal, showBand, setShowBand }) {
  const { summary: s, risk: r } = data;
  const full = s.forecast_intervals === s.expected_intervals;
  return C(
    'div',
    { className: 'content-stack' },
    C(
      'div',
      { className: 'stats-grid' },
      C(
        Stat,
        {
          label: 'Mean wind forecast',
          value: number(s.forecast_mean_mw),
          unit: 'MW',
          detail: 'Across covered delivery intervals'
        }
      ),
      C(
        Stat,
        {
          label: full ? 'Forecast wind energy' : 'Covered-interval wind energy',
          value: number(s.forecast_energy_mwh_covered == null ? null : s.forecast_energy_mwh_covered / 1000, 1),
          unit: 'GWh',
          detail: full ? '48 half-hours × forecast MW × 0.5h' : 'Partial coverage · not a daily total'
        }
      ),
      C(
        Stat,
        {
          label: 'Forecast coverage',
          value: `${s.forecast_intervals}`,
          unit: `/ ${s.expected_intervals}`,
          detail: full ? 'All delivery half-hours available' : 'Missing values are not filled',
          tone: full ? '' : 'warning'
        }
      ),
      C(
        Stat,
        {
          label: 'Oldest forecast at decision',
          value: number(data.max_forecast_age_hours, 1),
          unit: 'hours',
          detail: `${data.publication_count} publication ${data.publication_count === 1 ? 'vintage' : 'vintages'} selected`
        }
      )
    ),
    C(
      'div',
      { className: 'desk-grid' },
      C(
        Panel,
        {
          title: `Wind outlook · ${dateLabel(data.delivery_date, { weekday: 'short', day: 'numeric', month: 'short' })}`,
          subtitle: 'What was knowable before the buying decision',
          action: C(Badge, { tone: 'green' }, 'AS-OF SNAPSHOT')
        },
        C(LineChart, { points: data.points, reveal, showBand: showBand && r.status === 'available' }),
        C(
          'div',
          { className: 'chart-controls' },
          C(
            'label',
            { className: 'check-label' },
            C(
              'input',
              {
                type: 'checkbox',
                checked: showBand,
                disabled: r.status !== 'available',
                onChange: e => setShowBand(e.target.checked)
              }
            ),
            'Prior-only empirical range'
          ),
          C(
            'label',
            { className: 'check-label' },
            C('input', { type: 'checkbox', checked: reveal, onChange: e => setReveal(e.target.checked) }),
            'Reveal actuals · hindsight'
          )
        ),
        reveal && C(
          'div',
          { className: 'hindsight' },
          'Hindsight is on. Actuals and realised errors were not available at this decision.'
        )
      ),
      C(
        'aside',
        { className: 'decision-card' },
        C('span', { className: 'eyebrow' }, 'DECISION CONTEXT'),
        C('h2', null, 'One day ahead.', C('br'), 'No later revisions.'),
        C(
          'dl',
          null,
          C('dt', null, 'Decision day'),
          C('dd', null, dateLabel(data.decision_date)),
          C('dt', null, 'Delivery day'),
          C('dd', null, dateLabel(data.delivery_date)),
          C('dt', null, 'Decision cutoff'),
          C('dd', null, `${data.cutoff_local} GMT`),
          C('dt', null, 'Availability buffer'),
          C('dd', null, `${data.availability_buffer_minutes} minutes`),
          C('dt', null, 'Latest selected publication'),
          C(
            'dd',
            null,
            `${dateLabel(data.latest_publish_time, { day: 'numeric', month: 'short' })}, ${timeLabel(data.latest_publish_time)}`
          )
        ),
        C(
          'div',
          { className: 'context-note' },
          C(Icon, { name: 'shield', size: 18 }),
          C('span', null, 'Each half-hour uses its latest eligible forecast, not the latest forecast available today.')
        )
      )
    ),
    C(
      'div',
      { className: 'insight-grid' },
      C(
        'section',
        { className: 'risk-card' },
        C('div', { className: 'section-kicker' }, C(Icon, { name: 'chart', size: 18 }), 'HISTORICAL ERROR CONTEXT'),
        C(
          'h2',
          null,
          r.status === 'available' ? `A ${number(r.p90_shortfall_mw)} MW shortfall reference.` : 'Not enough earlier history yet.'
        ),
        C(
          'p',
          null,
          r.status === 'available' ? `The 90th percentile of positive forecast minus actual error, including zero for overdelivery. Based on ${r.sample_intervals} earlier half-hours across ${r.sample_decision_days} decision days.` : `This decision has ${r.sample_intervals} eligible earlier intervals across ${r.sample_decision_days} days. The pilot requires at least 168 intervals and seven prior decision days.`
        ),
        C(
          'small',
          null,
          'Only earlier January decisions and actual publications available before this cutoff. An exploratory stress reference, not a purchase recommendation.'
        )
      ),
      C(
        'section',
        { className: 'scope-card' },
        C('div', { className: 'section-kicker' }, C(Icon, { name: 'info', size: 18 }), 'KNOW THE BOUNDARY'),
        C('h3', null, 'Wind intelligence, not a buy order.'),
        C(
          'p',
          null,
          'National wind does not identify your portfolio’s wind entitlement, demand, existing hedges or other supply. No purchase volume, thermal dispatch or cost saving is inferred.'
        )
      )
    ),
    data.warnings.filter(w => !w.startsWith('SYNTHETIC')).map((w, i) => C('div', { key: i, className: 'notice' }, C(Icon, { name: 'info', size: 18 }), w)),
    C(IntervalTable, { points: data.points, reveal })
  );
}
function DailyBars({ daily, onSelect }) {
  const max = Math.max(...daily.map(d => d.mae_mw || 0), 1); return C(
    'div',
    { className: 'daily-bars' },
    daily.map(d => C(
      'button',
      {
        key: d.decision_date,
        className: `daily-bar ${d.coverage_pct < 100 ? 'partial' : ''}`,
        onClick: () => onSelect(d.decision_date),
        title: `Decision ${d.decision_date}: MAE ${number(d.mae_mw)} MW; ${d.coverage_pct}% paired coverage`,
        'aria-label': `Inspect decision ${d.decision_date}`
      },
      C(
        'span',
        { className: 'bar-track' },
        C(
          'span',
          { className: 'bar-fill', style: { height: `${d.mae_mw == null ? 0 : Math.max(3, d.mae_mw / max * 100)}%` } }
        )
      ),
      C('span', { className: 'bar-label' }, String(Number(d.decision_date.slice(-2))))
    ))
  );
}
function SimpleTable({ headers, rows }) {
  return C(
    'div',
    { className: 'table-scroll' },
    C(
      'table',
      null,
      C('thead', null, C('tr', null, headers.map((v, i) => C('th', { key: i }, v)))),
      C('tbody', null, rows.map((row, i) => C('tr', { key: i }, row.map((v, j) => C('td', { key: j }, v)))))
    )
  );
}
function Accuracy({ data, onSelect }) {
  const s = data.summary;
  const banner = C(
    'div',
    { className: 'review-banner' },
    C(Icon, { name: 'clock', size: 18 }),
    C(
      'span',
      null,
      'RETROSPECTIVE REVIEW',
      C(
        'small',
        null,
        'Forecasts are locked to each decision cutoff. Actuals use the latest revision in this snapshot.'
      )
    )
  );
  const stats = C(
    'div',
    { className: 'stats-grid' },
    C(
      Stat,
      { label: 'Mean absolute error', value: number(s.mae_mw), unit: 'MW', detail: 'Typical absolute deviation' }
    ),
    C(
      Stat,
      {
        label: 'Root mean square error',
        value: number(s.rmse_mw),
        unit: 'MW',
        detail: 'More sensitive to large misses'
      }
    ),
    C(
      Stat,
      {
        label: 'Signed bias · forecast − actual',
        value: signed(s.bias_mw),
        unit: 'MW',
        detail: s.bias_mw == null ? 'No paired observations' : s.bias_mw > 0 ? 'Positive: wind was overforecast' : s.bias_mw < 0 ? 'Negative: wind was underforecast' : 'No average signed bias'
      }
    ),
    C(
      Stat,
      {
        label: 'Weighted absolute error',
        value: number(s.wape_pct, 1),
        unit: '%',
        detail: 'Σ |error| ÷ Σ |actual| · zero-safe'
      }
    )
  );
  const daily = C(
    Panel,
    {
      title: 'When did the forecast miss?',
      subtitle: 'Daily MAE in MW · decision date in January · click a bar to inspect the delivery curve',
      action: C(
        Badge,
        { tone: s.coverage_pct === 100 ? 'green' : 'amber' },
        `${number(s.matched_intervals)} / ${number(s.expected_intervals)} paired`
      )
    },
    C(DailyBars, { daily: data.daily, onSelect }),
    C(
      'div',
      { className: 'chart-footer' },
      C('span', null, 'Each day is scored at the same selected cutoff.'),
      C('span', null, 'Amber bar = incomplete paired coverage')
    )
  );
  const hist = C(
    Panel,
    { title: 'Which direction is the risk?', subtitle: 'Distribution of signed half-hourly error in MW' },
    C(
      'div',
      { className: 'histogram' },
      data.histogram.map((b, i) => {
        const max = Math.max(...data.histogram.map(x => x.count), 1);
        return C(
          'div',
          {
            key: i,
            className: `hist-bin ${b.low >= 0 ? 'positive' : 'negative'}`,
            title: `${b.low} to ${b.high} MW: ${b.count} intervals`
          },
          C('div', { className: 'hist-track' }, C('div', { style: { height: `${b.count / max * 100}%` } })),
          C('small', null, number(b.low))
        );
      })
    ),
    C(
      'div',
      { className: 'direction-labels' },
      C('span', null, '← Actual exceeded forecast'),
      C('span', null, 'Forecast exceeded actual →')
    )
  );
  const references = [
    ['P90 absolute error', `${number(s.p90_abs_mw)} MW`],
    ['P90 shortfall · max(error, 0)', `${number(s.p90_shortfall_mw)} MW`],
    ['Intervals overforecast', `${number(s.overforecast_pct, 1)}%`],
    ['Net forecast − actual energy', `${signed(s.net_error_mwh == null ? null : s.net_error_mwh / 1000, 1)} GWh`],
    ['Paired coverage', `${number(s.coverage_pct, 1)}%`]
  ];
  const interpretation = C(
    Panel,
    { title: 'Make the error interpretable', subtitle: 'Interval-level references, not a procurement instruction' },
    C(
      'div',
      { className: 'metric-list' },
      references.map(([k, v]) => C('div', { key: k }, C('span', null, k), C('strong', null, v)))
    ),
    C(
      'p',
      { className: 'footnote' },
      'Monthly error statistics are hindsight. They are never reused as the risk range for an earlier decision.'
    )
  );
  const hourly = C(
    Panel,
    { title: 'Error by delivery hour', subtitle: 'Hourly MAE · each bar pools exact half-hour matches' },
    C(
      'div',
      { className: 'hourly-bars' },
      data.hourly.map(d => C(
        'div',
        { key: d.hour, title: `${d.hour}:00 · MAE ${number(d.mae_mw)} MW · n=${d.matched_intervals}` },
        C(
          'span',
          { style: { height: `${(d.mae_mw || 0) / Math.max(...data.hourly.map(x => x.mae_mw || 0), 1) * 110}px` } }
        ),
        C('small', null, d.hour % 3 === 0 ? String(d.hour).padStart(2, '0') : '')
      ))
    )
  );
  const horizon = C(
    Panel,
    { title: 'Error by forecast lead time', subtitle: 'Delivery start minus selected forecast publication' },
    C(
      SimpleTable,
      { headers: ['Lead time', 'Pairs', 'MAE MW', 'Bias MW'], rows: data.horizon.map(r => [r.label, r.matched_intervals, number(r.mae_mw), signed(r.bias_mw)]) }
    )
  );
  const worst = C(
    Panel,
    { title: 'Largest individual misses', subtitle: 'Review the exact delivery time and publication lineage' },
    C(
      SimpleTable,
      {
        headers: ['Decision', 'Delivery GMT', 'Forecast MW', 'Actual MW', 'Error MW', 'Forecast published GMT'], rows: data.worst_intervals.slice(0, 6).map(p => [
          C(
            'button',
            { className: 'text-button', onClick: () => onSelect(p.decision_date) },
            dateLabel(p.decision_date, { day: 'numeric', month: 'short' })
          ),
          `${dateLabel(p.start_time, { day: 'numeric', month: 'short' })} ${timeLabel(p.start_time)}`,
          number(p.forecast_mw), number(p.actual_mw), C('span', { className: 'amber-text' }, signed(p.error_mw)),
          `${dateLabel(p.publish_time, { day: 'numeric', month: 'short' })} ${timeLabel(p.publish_time)}`
        ])
      }
    )
  );
  return C(
    'div',
    { className: 'content-stack' },
    banner,
    stats,
    daily,
    C('div', { className: 'two-columns' }, hist, interpretation),
    C('div', { className: 'two-columns' }, hourly, horizon),
    worst
  );
}
function Method({ data }) {
  const p = data.provenance;
  const sections = [
    ['01 · Scope and selection', [
      'Decision dates: 1–31 January 2026. Delivery dates: 2 January–1 February. The last delivery day is included; 1 January delivery belongs to a December decision.',
      'For each startTime, choose the latest publishTime at or before decisionTime minus the availability buffer. Error = forecast MW − actual MW.',
      'The default 09:00 London cutoff is an illustrative desk deadline, not an exchange rule. Presets at 09:15 and 09:45 are planning assumptions. Custom cutoffs are sensitivity scenarios, not claims that a market remains open.',
      'publishTime is an availability proxy. A configurable 0–60 minute buffer represents hypothetical ingestion delay; the archive cannot prove actual arrival time.'
    ]],
    ['02 · Honest comparisons', [
      'FUELHH/WIND and WINDFOR are matched only at identical UTC start times. The expected grid is the London delivery day’s half-hours. No interpolation, nearest-neighbour join or zero-filling is used.',
      'If a forecast is hourly, alternate half-hours remain missing. Energy is the sum of covered forecast MW × 0.5 hours, not an inferred full-day total.',
      'Identical duplicate versions collapse. Conflicting values at the same target and publication time are quarantined. A missing forecast is not a zero forecast.',
      'Errors describe the supplied operational series, not pure weather-model error. Curtailment, operational effects and revisions are not separately explained by these inputs.'
    ]],
    ['03 · Risk without future information', [
      'The empirical range pools actual minus forecast residuals from earlier January decisions only. Historical forecasts use the same cutoff and buffer. Actual values must have been published, and their interval must have ended, before the current cutoff.',
      'At least seven previous decision days and 168 paired intervals are required. Earlier decisions show insufficient history. Actuals missing publishTime are excluded from calibration, but can be scored retrospectively.',
      'The 10th–90th percentile residual range is exploratory. It is not an 80% calibrated prediction interval, assumes no guaranteed independence, and does not validate performance out of sample.'
    ]],
    ['04 · Quantify, do not overclaim', [
      'MAE: mean absolute error. RMSE: square root of mean squared error. Bias: mean forecast minus actual. Positive bias means wind was overforecast.',
      'WAPE: 100 × sum absolute errors / sum absolute actuals. Undefined when the denominator is zero. Unlike MAPE, it does not divide each near-zero interval separately.',
      'P90 shortfall: 90th percentile of max(forecast − actual, 0), including zeros. It is an interval reference, not a daily energy quantile.',
      'National operationally metered wind is not total UK renewable output or a utility-owned portfolio. Demand, other generation, hedges and prices are outside this pilot.'
    ]]
  ];
  const hero = C(
    'section',
    { className: 'method-hero' },
    C('span', { className: 'eyebrow' }, 'AUDITABLE BY DESIGN'),
    C('h2', null, 'The timestamp is part of the forecast.'),
    C(
      'p',
      null,
      'A good-looking curve is not enough. This pilot keeps the decision date, delivery date, publication time and outturn revision policy separate.'
    )
  );
  const cards = sections.map(([title, paragraphs]) => C(
    Panel,
    { key: title, title },
    C('div', { className: 'prose' }, paragraphs.map((text, i) => C('p', { key: i }, text)))
  ));
  const provenance = [['Data mode', p.mode === 'synthetic' ? 'SYNTHETIC · NOT MARKET OBSERVATIONS' : 'Real Elexon snapshot'], ['Source', p.source], ['Retrieved at', p.retrieved_at || 'Not applicable · generated test fixture'], ['Revision policy', p.actual_revision_policy], ['Alignment', p.alignment], ['SHA-256', p.snapshot_sha256]];
  const quality = C(
    'div',
    { className: 'two-columns quality' },
    ['forecast_quality', 'actual_quality'].map(key => C(
      'div',
      { key },
      C('h3', null, key === 'forecast_quality' ? 'Forecast validation' : 'Actual validation'),
      C(
        'dl',
        null,
        Object.entries(p[key] || {}).map(([k, v]) => C('div', { key: k }, C('dt', null, k.replaceAll('_', ' ')), C('dd', null, number(v))))
      )
    ))
  );
  const audit = C(
    Panel,
    { title: 'Snapshot provenance', subtitle: 'The same identifier is included in CSV exports' },
    C(
      'div',
      { className: 'provenance-grid' },
      provenance.map(([k, v]) => C('div', { key: k }, C('span', null, k), C('strong', { className: k === 'SHA-256' ? 'hash' : '' }, v)))
    ),
    quality,
    p.ingest_quality && C(
      'details',
      { className: 'raw-quality' },
      C('summary', null, 'Raw ingestion validation before normalization'),
      C('pre', null, JSON.stringify(p.ingest_quality, null, 2))
    )
  );
  const links = [['Elexon · FUELHH stream', 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream'], ['Elexon · WINDFOR stream', 'https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream'], ['Elexon · Wind forecast coverage', 'https://bmrs.elexon.co.uk/api-documentation/endpoint/forecast/generation/wind'], ['EPEX SPOT · Trading products', 'https://www.epexspot.com/en/tradingproducts'], ['Nord Pool · N2EX auction', 'https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction']];
  const refs = C(
    Panel,
    { title: 'Primary references' },
    C(
      'div',
      { className: 'source-links' },
      links.map(([label, url]) => C('a', { key: label, href: url, target: '_blank', rel: 'noreferrer' }, label, ' ↗'))
    )
  );
  return C(
    'div',
    { className: 'content-stack' },
    hero,
    C('div', { className: 'two-columns' }, ...cards.slice(0, 2)),
    C('div', { className: 'two-columns' }, ...cards.slice(2)),
    audit,
    refs
  );
}
function App() {
  const [tab, setTab] = useState('desk'), [source, setSource] = useState('real'), [day, setDay] = useState('2026-01-15'), [cutoff, setCutoff] = useState('09:00'), [buffer, setBuffer] = useState(0), [reveal, setReveal] = useState(false), [showBand, setShowBand] = useState(true), [start, setStart] = useState('2026-01-01'), [end, setEnd] = useState('2026-01-31');
  const isAccuracy = tab === 'accuracy';
  const api = useApi(isAccuracy ? '/api/accuracy' : '/api/snapshot', isAccuracy ? { start_date: start, end_date: end, cutoff, buffer_minutes: buffer, source } : { decision_date: day, cutoff, buffer_minutes: buffer, reveal_actual: reveal, source });
  function selectDay(d) { setDay(d); setReveal(true); setTab('desk'); window.scrollTo({ top: 0, behavior: 'smooth' }); }
  const titles = {
    desk: ['Decision desk', 'A clearer view of tomorrow’s wind.'],
    accuracy: ['Accuracy lab', 'Know the size and direction of the miss.'],
    method: ['Data & methodology', 'Trust the data. Understand the limits.']
  };
  const exportUrl = '/api/export.csv?' + query({
    start_date: isAccuracy ? start : day,
    end_date: isAccuracy ? end : day,
    cutoff,
    buffer_minutes: buffer,
    source,
    reveal_actual: isAccuracy || reveal
  });
  return C(
    'div',
    { className: 'app-shell' },
    C('a', { href: '#main', className: 'skip-link' }, 'Skip to main content'),
    C(
      'aside',
      { className: 'sidebar' },
      C(
        'div',
        { className: 'brand' },
        C('div', { className: 'brand-icon' }, C(Icon, { name: 'wind', size: 25 })),
        C('div', null, C('strong', null, 'windward'), C('span', null, 'DAY-AHEAD INTELLIGENCE'))
      ),
      C('div', { className: 'workspace-label' }, 'WORKSPACE'),
      C(
        'nav',
        { 'aria-label': 'Main navigation' },
        [['desk', 'grid', 'Decision desk'], ['accuracy', 'chart', 'Accuracy lab'], ['method', 'shield', 'Data & methodology']].map(([id, icon, label]) => C(
          'button',
          {
            key: id,
            className: tab === id ? 'nav-button active' : 'nav-button',
            onClick: () => setTab(id),
            'aria-current': tab === id ? 'page' : undefined
          },
          C(Icon, { name: icon }),
          label,
          tab === id && C('span', { className: 'active-dot' })
        ))
      ),
      C(
        'div',
        { className: 'sidebar-bottom' },
        C('div', { className: 'pilot-note' }, C('span', { className: 'status-dot' }), 'JANUARY 2026 PILOT'),
        C('p', null, 'National wind. Decision-time context. Transparent uncertainty.'),
        C(
          'a',
          { href: '/review', className: 'review-link' },
          C(Icon, { name: 'code', size: 16 }),
          'Technical review ↗'
        ),
        C(
          'div',
          { className: 'sidebar-source' },
          'FUELHH / WIND + WINDFOR',
          C('span', null, 'Elexon-only data specification')
        )
      )
    ),
    C(
      'div',
      { className: 'main-shell' },
      C(
        'header',
        { className: 'topbar' },
        C(
          'div',
          { className: 'breadcrumb' },
          'Pilot workspace',
          C('span', null, '/'),
          C('strong', null, titles[tab][0])
        ),
        C(
          'div',
          { className: 'topbar-right' },
          C('span', { className: 'timezone' }, C(Icon, { name: 'clock', size: 15 }), 'Europe/London · GMT'),
          C(
            'label',
            { className: 'source-select' },
            'Dataset',
            C(
              'select',
              { 'aria-label': 'Dataset', value: source, onChange: e => { setSource(e.target.value); setReveal(false); } },
              C('option', { value: 'real' }, 'Elexon snapshot'),
              C('option', { value: 'synthetic' }, 'Synthetic sandbox')
            )
          )
        )
      ),
      source === 'synthetic' && C(
        'div',
        { className: 'synthetic-banner', role: 'status' },
        C('strong', null, 'SYNTHETIC SANDBOX'),
        C(
          'span',
          null,
          'Generated test data only. These values are not Elexon observations or January 2026 findings.'
        )
      ),
      C(
        'main',
        { id: 'main' },
        C(
          'div',
          { className: 'page-heading' },
          C(
            'div',
            null,
            C(
              'span',
              { className: 'eyebrow' },
              isAccuracy ? 'FORECAST PERFORMANCE' : tab === 'method' ? 'METHODOLOGY & LINEAGE' : 'D+1 WIND OUTLOOK'
            ),
            C('h1', null, titles[tab][0]),
            C('p', null, titles[tab][1])
          ),
          C(
            'a',
            {
              className: `export-button ${!api.data ? 'disabled' : ''}`,
              href: api.data ? exportUrl : undefined,
              'aria-disabled': !api.data
            },
            C(Icon, { name: 'download', size: 17 }),
            'Export CSV'
          )
        ),
        tab !== 'method' && C(
          'div',
          { className: 'toolbar' },
          isAccuracy ? C(
            'div',
            { className: 'date-range' },
            C(
              'label',
              null,
              'Decision range',
              C(
                'input',
                {
                  'aria-label': 'Start decision date',
                  type: 'date',
                  min: '2026-01-01',
                  max: end,
                  value: start,
                  onChange: e => {
                    if (e.target.value)
                      setStart(e.target.value);
                  }
                }
              )
            ),
            C('span', null, '→'),
            C(
              'label',
              null,
              'Through',
              C(
                'input',
                {
                  'aria-label': 'End decision date',
                  type: 'date',
                  min: start,
                  max: '2026-01-31',
                  value: end,
                  onChange: e => {
                    if (e.target.value)
                      setEnd(e.target.value);
                  }
                }
              )
            )
          ) : C(
            'div',
            { className: 'decision-picker' },
            C(
              'label',
              null,
              'Decision date',
              C(
                'input',
                {
                  'aria-label': 'Decision date',
                  type: 'date',
                  min: '2026-01-01',
                  max: '2026-01-31',
                  value: day,
                  onChange: e => {
                    if (e.target.value)
                      setDay(e.target.value);
                  }
                }
              )
            ),
            C(
              'div',
              { className: 'date-arrows' },
              C(
                'button',
                {
                  'aria-label': 'Previous decision day',
                  disabled: day === '2026-01-01',
                  onClick: () => setDay(shiftDate(day, -1))
                },
                '‹'
              ),
              C(
                'button',
                {
                  'aria-label': 'Next decision day',
                  disabled: day === '2026-01-31',
                  onClick: () => setDay(shiftDate(day, 1))
                },
                '›'
              )
            )
          ),
          C('div', { className: 'toolbar-separator' }),
          C(
            'label',
            null,
            'Decision cutoff · GMT',
            C(
              'input',
              {
                'aria-label': 'Decision cutoff',
                type: 'time',
                value: cutoff,
                onChange: e => {
                  if (e.target.value)
                    setCutoff(e.target.value);
                }
              }
            )
          ),
          C(
            'div',
            { className: 'cutoff-presets' },
            [['09:00', 'Desk'], ['09:15', 'Pre-EPEX'], ['09:45', 'Pre-N2EX']].map(([v, l]) => C(
              'button',
              {
                key: v,
                title: 'Illustrative desk cutoff, not an exchange rule',
                className: cutoff === v ? 'selected' : '',
                onClick: () => setCutoff(v)
              },
              l
            ))
          ),
          C(
            'label',
            { className: 'buffer-label' },
            'Availability buffer',
            C(
              'select',
              { 'aria-label': 'Availability buffer', value: buffer, onChange: e => setBuffer(Number(e.target.value)) },
              [0, 5, 15, 30, 60].map(v => C('option', { key: v, value: v }, `${v} min`))
            )
          )
        ),
        api.loading ? C(Loading) : api.error ? C(Empty, { error: api.error, onDemo: () => setSource('synthetic') }) : tab === 'desk' ? C(Decision, { data: api.data, reveal, setReveal, showBand, setShowBand }) : isAccuracy ? C(Accuracy, { data: api.data, onSelect: selectDay }) : C(Method, { data: api.data }),
        C(
          'footer',
          { className: 'page-footer' },
          C('span', null, 'Windward / January 2026 pilot'),
          C(
            'span',
            null,
            source === 'synthetic' ? 'Synthetic fixture · not for procurement' : 'Elexon operational wind series · not total renewable generation'
          )
        )
      )
    )
  );
}
window.ReactDOM.createRoot(document.getElementById('root')).render(C(App));

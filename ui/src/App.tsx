import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, ArrowRight, Bookmark, Boxes, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Database, Download, FileBarChart2, Filter, Gauge, GitBranch, Menu, Search, Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Tags, X, RefreshCw, type LucideIcon } from 'lucide-react'
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef, type SortingState, type VisibilityState } from '@tanstack/react-table'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { apiUrl, fetchEvents, fetchInvestigations, fetchOptions, fetchOverview, fetchReports, fetchReviews, fetchStatus, type Cluster, type Investigation, type ReportFile } from './api'
import type { AppStatus, EventRecord, FilterState, Options, OverviewData } from './types'

const emptyFilters: FilterState = { date_from: '', date_to: '', make: '', model: '', plant: '', category: '' }
const navItems: { label: string; to: string; icon: LucideIcon; group?: string }[] = [
  { label: 'Overview', to: '/', icon: Gauge, group: 'WORKSPACE' },
  { label: 'Failure analytics', to: '/failures', icon: Activity },
  { label: 'Root cause intelligence', to: '/root-causes', icon: GitBranch },
  { label: 'Data explorer', to: '/explorer', icon: Database, group: 'ANALYSIS' },
  { label: 'Sentiment intelligence', to: '/sentiment', icon: Sparkles },
  { label: 'Reports & exports', to: '/reports', icon: FileBarChart2, group: 'DELIVERY' },
]
const titles: Record<string, { title: string; eyebrow: string; subtitle: string }> = {
  '/': { title: 'Automotive Intelligence', eyebrow: 'OVERVIEW', subtitle: 'Monitor quality events, discover recurring failure patterns, and investigate root causes.' },
  '/failures': { title: 'Failure analytics', eyebrow: 'QUALITY SIGNALS', subtitle: 'Explore complaint codes, component patterns, and recorded corrective actions.' },
  '/root-causes': { title: 'Root cause intelligence', eyebrow: 'INVESTIGATION WORKSPACE', subtitle: 'Trace recurring patterns back to source records and diagnostic evidence.' },
  '/explorer': { title: 'Data explorer', eyebrow: 'EVENT RECORDS', subtitle: 'Search and inspect source events alongside derived analytical fields.' },
  '/sentiment': { title: 'Sentiment intelligence', eyebrow: 'CUSTOMER VOICE', subtitle: 'Review experience themes and sentiment when an authorized collection is available.' },
  '/reports': { title: 'Reports & exports', eyebrow: 'DELIVERY', subtitle: 'Access analysis reports and generated datasets from this workspace.' },
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [options, setOptions] = useState<Options | null>(null)
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [filters, setFilters] = useState<FilterState>(emptyFilters)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)
  const [selected, setSelected] = useState<EventRecord | null>(null)
  const load = useCallback(async (showRefresh = false) => {
    showRefresh ? setRefreshing(true) : setLoading(true)
    setError('')
    try {
      const [s, o, d] = await Promise.all([fetchStatus(), fetchOptions(), fetchOverview(filters)])
      setStatus(s); setOptions(o); setOverview(d)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load project data') }
    finally { setLoading(false); setRefreshing(false) }
  }, [filters])
  useEffect(() => { void load() }, [load])
  useEffect(() => { setMobileNav(false) }, [location.pathname])
  const page = titles[location.pathname] ?? titles['/']
  const routeContent = <Routes>
    <Route path="/" element={<OverviewPage data={overview} loading={loading} onSelect={setSelected} onCategory={(c) => navigate(`/explorer?search=${encodeURIComponent(c)}`)} />} />
    <Route path="/failures" element={<FailurePage data={overview} loading={loading} onSelect={setSelected} onCategory={(c) => navigate(`/explorer?search=${encodeURIComponent(c)}`)} />} />
    <Route path="/root-causes" element={<RootCausePage />} />
    <Route path="/explorer" element={<ExplorerPage filters={filters} onSelect={setSelected} />} />
    <Route path="/sentiment" element={<SentimentPage count={status?.review_count ?? 0} />} />
    <Route path="/reports" element={<ReportsPage />} />
    <Route path="*" element={<OverviewPage data={overview} loading={loading} onSelect={setSelected} onCategory={(c) => navigate(`/explorer?search=${encodeURIComponent(c)}`)} />} />
  </Routes>
  return <div className="app-shell">
    <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''} ${mobileNav ? 'sidebar--open' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><span className="brand-a">A</span><span className="brand-spark" /></div>{!collapsed && <div className="brand-copy"><b>autoinsight<span>AI</span></b><small>QUALITY INTELLIGENCE</small></div>}<button className="icon-btn collapse-btn" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar"><ChevronLeft size={15} /></button></div>
      <div className="workspace-switch"><div className="workspace-icon"><Boxes size={15} /></div>{!collapsed && <><span>Engineering workspace</span><ChevronDown size={13} className="muted-icon" /></>}</div>
      <nav className="main-nav" aria-label="Main navigation">
        {navItems.map((item) => <div key={item.to}>{item.group && !collapsed && <div className="nav-group-label">{item.group}</div>}<NavLink to={item.to} end={item.to === '/'} title={collapsed ? item.label : undefined} className={({ isActive }) => `nav-item ${isActive ? 'nav-item--active' : ''}`}><item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.to === '/root-causes' && !collapsed && <span className="nav-pill">AI</span>}</NavLink></div>)}
      </nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><div className="note-icon"><ShieldCheck size={15} /></div>{!collapsed && <div><b>Analysis environment</b><span>Local · Read only</span></div>}</div><button className="nav-item" title="Settings are not configured" onClick={() => setError('No external data source is configured. The dashboard reads local project outputs.')}><Settings2 size={17} /><span>Data sources</span></button><div className="sidebar-footer">{!collapsed && <span>AutoInsight AI <i>v1.0.0</i></span>}<button className="icon-btn" aria-label="Help" onClick={() => setError('Help: navigate through the event analyses, apply filters, and download existing reports.')}><CircleHelp size={15} /></button></div></div>
    </aside>
    {mobileNav && <button className="mobile-scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
    <main className="main-shell">
      <header className="topbar"><div className="topbar-left"><button className="icon-btn mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={19} /></button><span className="breadcrumb-root">Workspace</span><ChevronRight size={13} /><span className="breadcrumb-current">{page.title}</span></div><div className="topbar-actions"><span className="dataset-status"><i />{status ? `${status.event_count.toLocaleString()} records` : 'Connecting'}</span><span className="topbar-divider" /><span className="refresh-time">{status?.last_refresh ? `Updated ${formatRelative(status.last_refresh)}` : 'Awaiting data'}</span><button className={`icon-btn refresh-button ${refreshing ? 'spinning' : ''}`} aria-label="Refresh data" onClick={() => void load(true)}><RefreshCw size={15} /></button></div></header>
      <div className="page-scroll"><div className="page-wrap">
        {error && <div className="error-banner"><AlertTriangle size={16} /><span>{error}</span><button onClick={() => setError('')}><X size={15} /></button></div>}
        <div className="page-heading"><div><div className="eyebrow"><span />{page.eyebrow}</div><h1>{page.title}</h1><p>{page.subtitle}</p></div>{location.pathname === '/' && <div className="heading-mark"><div className="heading-mark-ring"><Activity size={18} /></div><span>Intelligence<br />behind every failure</span></div>}</div>
        {(location.pathname === '/' || location.pathname === '/failures') && options && <FilterBar options={options} filters={filters} onChange={setFilters} />}
        {routeContent}
        <footer className="page-footer"><span>AutoInsight AI <span className="footer-dot">·</span> Intelligence Behind Every Failure.</span><span>Local analysis environment <i className="footer-dot">·</i> Source-linked insights</span></footer>
      </div></div>
    </main>
    {selected && <EventDrawer event={selected} onClose={() => setSelected(null)} />}
    {mobileNav && <div className="mobile-close-area" onClick={() => setMobileNav(false)} />}
  </div>
}

function FilterBar({ options, filters, onChange }: { options: Options; filters: FilterState; onChange: (f: FilterState) => void }) {
  const update = (key: keyof FilterState, value: string) => onChange({ ...filters, [key]: value })
  const active = Object.values(filters).some(Boolean)
  return <div className="filter-bar"><div className="filter-label"><SlidersHorizontal size={14} /><span>FILTERS</span></div><label className="filter-control date-control"><CalendarDays size={14} /><input aria-label="Start date" type="date" min={options.date_min ?? undefined} max={filters.date_to || options.date_max || undefined} value={filters.date_from} onChange={(e) => update('date_from', e.target.value)} /></label><span className="filter-date-separator">to</span><label className="filter-control date-control"><input aria-label="End date" type="date" min={filters.date_from || options.date_min || undefined} max={options.date_max ?? undefined} value={filters.date_to} onChange={(e) => update('date_to', e.target.value)} /></label><FilterSelect label="Make" value={filters.make} values={options.makes} onChange={(v) => update('make', v)} /><FilterSelect label="Model" value={filters.model} values={options.models} onChange={(v) => update('model', v)} /><FilterSelect label="Plant" value={filters.plant} values={options.plants} onChange={(v) => update('plant', v)} /><FilterSelect label="Issue" value={filters.category} values={options.categories} onChange={(v) => update('category', v)} />{active && <button className="reset-filter" onClick={() => onChange(emptyFilters)}><X size={13} />Reset</button>}</div>
}
function FilterSelect({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (v: string) => void }) { return <label className={`filter-select ${value ? 'has-value' : ''}`}><span>{label}</span><select value={value} aria-label={`Filter by ${label}`} onChange={(e) => onChange(e.target.value)}><option value="">All {label.toLowerCase()}s</option>{values.map((v) => <option key={v} value={v}>{v}</option>)}</select><ChevronDown size={12} /></label> }

function OverviewPage({ data, loading, onSelect, onCategory }: { data: OverviewData | null; loading: boolean; onSelect: (r: EventRecord) => void; onCategory: (c: string) => void }) {
  if (loading && !data) return <LoadingState />
  if (!data) return <ErrorState />
  const total = data.summary.denominator || 1
  return <motion.div className="page-content" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .25 }}>
    <div className="metric-grid">
      <MetricCard label="Total events" value={data.summary.total_events.toLocaleString()} detail="Recorded quality events" icon={Activity} accent="cyan" />
      <MetricCard label="Unique event IDs" value={data.summary.unique_event_ids.toLocaleString()} detail="Traceable source records" icon={Database} accent="blue" />
      <MetricCard label="Distinct components" value={data.summary.distinct_components.toLocaleString()} detail="From supplied entity tags" icon={Boxes} accent="violet" hint="Entity labels are available on 5 of 1,000 source records." />
      <MetricCard label="Issue categories" value={data.summary.distinct_categories.toLocaleString()} detail="Text-mined groupings" icon={Tags} accent="amber" />
    </div>
    <div className="chart-grid chart-grid--hero"><ChartPanel title="Event volume" subtitle="Opening date · Monthly records" badge={`${data.monthly.length} MONTHS`} className="span-2"><div className="chart-legend"><span className="legend-dot cyan" />Quality events</div><div className="area-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.monthly} margin={{ top: 12, right: 6, bottom: 0, left: -16 }}><defs><linearGradient id="eventFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5bd3e9" stopOpacity={.2} /><stop offset="95%" stopColor="#5bd3e9" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#202a39" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="month" tickFormatter={(v) => v.slice(2)} axisLine={false} tickLine={false} tick={{ fill: '#78869a', fontSize: 11 }} minTickGap={24} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#78869a', fontSize: 11 }} allowDecimals={false} /><Tooltip content={<ChartTooltip suffix="events" />} /><Area type="monotone" dataKey="events" stroke="#59d0e7" strokeWidth={2} fill="url(#eventFill)" activeDot={{ r: 4, fill: '#59d0e7', stroke: '#10202b', strokeWidth: 3 }} /></AreaChart></ResponsiveContainer></div><div className="chart-footnote"><span><i className="status-dot" />{total.toLocaleString()} records in current view</span><span>Event counts · no exposure denominator</span></div></ChartPanel>
      <ChartPanel title="Failure categories" subtitle="Narrative keyword grouping" badge="PRIMARY TAG"><div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.issues} dataKey="count" nameKey="label" innerRadius={64} outerRadius={88} paddingAngle={3} stroke="none" onClick={(d) => onCategory(d.label)} style={{ cursor: 'pointer' }}>{data.issues.map((_, i) => <Cell key={i} fill={['#4cd2e4', '#6479ed', '#a179ea', '#ecb65c', '#ed846b', '#708093'][i % 6]} />)}</Pie><Tooltip content={<ChartTooltip suffix="events" />} /></PieChart></ResponsiveContainer><div className="donut-center"><strong>{total.toLocaleString()}</strong><small>EVENTS</small></div></div><div className="legend-list">{data.issues.slice(0, 5).map((item, i) => <button key={item.label} className="legend-row" onClick={() => onCategory(item.label)}><i style={{ background: ['#4cd2e4', '#6479ed', '#a179ea', '#ecb65c', '#ed846b'][i] }} /><span>{item.label}</span><b>{item.count.toLocaleString()}</b><small>{pct(item.count, total)}%</small></button>)}</div></ChartPanel>
    </div>
    <div className="chart-grid chart-grid--three"><ChartPanel title="Top failure components" subtitle="Provided entity tags" badge="5 TAGGED RECORDS"><HorizontalBars data={data.components} color="#5bd3e9" empty="Source component tags are populated on only 5 records." onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Plant distribution" subtitle="Events by build plant" badge="8 PLANTS"><HorizontalBars data={data.plants.slice(0, 7)} color="#7985ed" /></ChartPanel><ChartPanel title="Failure conditions" subtitle="Provided entity tags" badge="SPARSE DATA"><HorizontalBars data={data.conditions} color="#b18bea" empty="Source condition tags are populated on only 5 records." /></ChartPanel></div>
    <RecentEvents rows={data.recent} onSelect={onSelect} />
  </motion.div>
}

function FailurePage({ data, loading, onSelect, onCategory }: { data: OverviewData | null; loading: boolean; onSelect: (r: EventRecord) => void; onCategory: (c: string) => void }) {
  if (loading && !data) return <LoadingState />
  if (!data) return <ErrorState />
  return <motion.div className="page-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
    <div className="section-banner"><div className="banner-icon"><Activity size={18} /></div><div><b>Failure investigation workspace</b><p>Counts reflect events in the selected view. These are not vehicle failure rates; exposure denominators are unavailable.</p></div><span>{data.summary.denominator.toLocaleString()} RECORD DENOMINATOR</span></div>
    <div className="metric-grid metric-grid--compact"><MetricCard label="Events in view" value={data.summary.total_events.toLocaleString()} detail="Filtered source records" icon={Database} accent="cyan" /><MetricCard label="Complaint types" value={String(new Set(data.complaints.map((x) => x.label)).size)} detail="Observed coded groups" icon={Tags} accent="blue" /><MetricCard label="Recorded causal codes" value={data.summary.distinct_causal_codes.toString()} detail="Distinct source classifications" icon={GitBranch} accent="violet" /><MetricCard label="Tagged component-condition pairs" value={data.combinations.reduce((a, x) => a + x.count, 0).toString()} detail="Provided entities · 5 tagged records" icon={Settings2} accent="amber" /></div>
    <div className="chart-grid chart-grid--two"><ChartPanel title="Complaint code breakdown" subtitle="Click a category to inspect matching event records" badge="SOURCE FIELD"><HorizontalBars data={data.complaints} color="#51cfe2" onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Causal code breakdown" subtitle="Recorded causal classifications" badge="SOURCE FIELD"><HorizontalBars data={data.causes} color="#777fec" onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Issue category mix" subtitle="Rule-based text groupings · exploratory" badge="MINED"><HorizontalBars data={data.issues} color="#a17ce5" onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Failure components" subtitle="Provided entity tags · sparse coverage" badge="5 TAGGED RECORDS"><HorizontalBars data={data.components} color="#60cbbb" empty="Failure component entities are available on only 5 records." onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Component × condition" subtitle="Parsed source entities · sparse coverage" badge="5 TAGGED RECORDS"><HorizontalBars data={data.combinations} color="#60cbbb" empty="Component and condition entities are available on only 5 records." onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Failure conditions" subtitle="Provided entity tags · sparse coverage" badge="SOURCE ENTITIES"><HorizontalBars data={data.conditions} color="#b18bea" empty="Failure condition tags are unavailable." onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Recorded corrective actions" subtitle="Fix condition tags from source entity fields" badge="SOURCE ENTITIES"><HorizontalBars data={data.fixes} color="#e8ac62" empty="Corrective action tags are unavailable." onClick={(label) => onCategory(label)} /></ChartPanel><ChartPanel title="Vehicle model distribution" subtitle="Event counts by model" badge="2020 MODEL YEAR"><HorizontalBars data={data.models.slice(0, 10)} color="#7985ed" /></ChartPanel><ChartPanel title="Build plant distribution" subtitle="Event counts by build plant" badge="SOURCE FIELD"><HorizontalBars data={data.plants} color="#5fc1d1" /></ChartPanel></div>
    <RecentEvents rows={data.recent} onSelect={onSelect} />
  </motion.div>
}

function RootCausePage() {
  const navigate = useNavigate()
  const [data, setData] = useState<{ denominator: number; findings: Investigation[]; clusters: Cluster[] } | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { fetchInvestigations().then(setData).catch((e) => setError(String(e))) }, [])
  if (error) return <ErrorState message={error} />
  if (!data) return <LoadingState />
  return <motion.div className="page-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
    <div className="evidence-banner"><div className="evidence-symbol"><Sparkles size={17} /></div><div><b>Evidence-led investigation</b><p>These are observed text groupings and supporting records. Potential mechanisms remain hypotheses until validated by engineering review.</p></div><span className="evidence-label">OBSERVED ≠ CONFIRMED</span></div>
    <div className="investigation-layout"><section className="finding-column"><div className="section-heading"><div><h2>Recurring issue patterns</h2><p>Ranked by source record count · n = {data.denominator.toLocaleString()}</p></div><span className="neutral-chip">{data.findings.length} GROUPS</span></div>{data.findings.map((f, i) => <FindingCard key={f.category} finding={f} rank={i + 1} onOpen={(id) => navigate(`/explorer?search=${encodeURIComponent(id)}`)} />)}</section><aside className="cluster-column"><div className="section-heading"><div><h2>Cluster explorer</h2><p>TF-IDF term summaries</p></div><span className="ai-chip"><Sparkles size={12} />ML</span></div><div className="cluster-list">{data.clusters.map((c) => <button className="cluster-card cluster-card--button" key={c.cluster} onClick={() => navigate(`/explorer?cluster=${c.cluster}`)} title={`Explore ${c.records} records in this cluster`}><div className="cluster-head"><span className="cluster-id">C{String(c.cluster + 1).padStart(2, '0')}</span><span>{Number(c.records).toLocaleString()} records <ArrowRight size={11} /></span></div><div className="cluster-terms">{String(c.top_terms).split(';').slice(0, 6).map((t) => <span key={t}>{t.trim()}</span>)}</div><div className="cluster-foot"><span>Unsupervised group</span><span>Terms only · validate manually</span></div></button>)}</div><div className="method-note"><ShieldCheck size={15} /><span>Cluster labels summarize recurring vocabulary. They do not assign a causal finding.</span></div></aside></div>
  </motion.div>
}
function FindingCard({ finding, rank, onOpen }: { finding: Investigation; rank: number; onOpen: (id: string) => void }) {
  const [expanded, setExpanded] = useState(rank === 1)
  return <article className="finding-card"><button className="finding-toggle" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}><div className="finding-rank">{String(rank).padStart(2, '0')}</div><div className="finding-title"><span className="observed-tag"><i />OBSERVED PATTERN</span><h3>{finding.category}</h3><p>{finding.count.toLocaleString()} events <i>·</i> {pct(finding.count, finding.denominator)}% of {finding.denominator.toLocaleString()}</p></div><div className="finding-count"><b>{finding.count.toLocaleString()}</b><span>EVENTS</span></div><ChevronDown size={16} className={`finding-chevron ${expanded ? 'rotated' : ''}`} /></button>{expanded && <div className="finding-detail"><div className="hypothesis-row"><div className="hypothesis-mark"><CircleHelp size={15} /></div><div><b>Next investigation</b><p>{finding.hypothesis} Review whether common diagnostic codes, build cohorts, and repair outcomes recur across these records.</p></div></div><div className="finding-evidence-grid"><div><span className="mini-label">RELATED CAUSAL CODES</span>{finding.causes.slice(0, 3).map((c) => <div className="evidence-line" key={c.label}><span>{c.label}</span><b>{c.count}</b></div>)}</div><div><span className="mini-label">RECORDED REPAIR ACTIONS</span>{finding.fixes.slice(0, 3).map((c) => <div className="evidence-line" key={c.label}><span>{c.label}</span><b>{c.count}</b></div>)}</div></div><span className="mini-label narrative-label">REPRESENTATIVE SOURCE NARRATIVES</span>{finding.samples.map((s) => <button className="source-sample source-sample--button" key={s['Event id']} onClick={() => onOpen(s['Event id'])}><span className="mono-id">{s['Event id']} · OPEN RECORD</span><p>{truncate(s.CAUSAL_VERBATIM || s.CUSTOMER_VERBATIM || 'No narrative was recorded.', 360)}</p></button>)}</div>}</article>
}

function ExplorerPage({ filters, onSelect }: { filters: FilterState; onSelect: (r: EventRecord) => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const initialParams = new URLSearchParams(location.search)
  const initialCategory = initialParams.get('category') ?? filters.category
  const initialCluster = initialParams.get('cluster') ?? ''
  const [search, setSearch] = useState(initialParams.get('search') ?? '')
  const [debounced, setDebounced] = useState('')
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState(25)
  const [rows, setRows] = useState<EventRecord[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [busy, setBusy] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([{ id: 'Opened date_parsed', desc: true }])
  const [error, setError] = useState('')
  useEffect(() => { const t = setTimeout(() => { setDebounced(search); setPageIndex(0) }, 250); return () => clearTimeout(t) }, [search])
  const sort = sorting[0]
  useEffect(() => {
    setBusy(true); setError('')
    const params = new URLSearchParams({ page: String(pageIndex + 1), page_size: String(pageSize), sort_by: sort?.id ?? 'Opened date_parsed', sort_dir: sort?.desc === false ? 'asc' : 'desc' })
    if (debounced) params.set('q', debounced)
    if (initialCluster) params.set('cluster', initialCluster)
    for (const [k, v] of Object.entries({ ...filters, category: initialCategory })) if (v) params.set(k, v)
    fetchEvents(params).then((result) => { setRows(result.rows); setTotal(result.total); setPages(result.pages) }).catch((e) => setError(String(e))).finally(() => setBusy(false))
  }, [filters, initialCategory, initialCluster, debounced, pageIndex, pageSize, sort?.id, sort?.desc])
  const columns = useMemo<ColumnDef<EventRecord>[]>(() => [
    { accessorKey: 'Event id', header: 'EVENT ID', cell: (ctx) => <span className="mono-id">{String(ctx.getValue())}</span> },
    { accessorKey: 'Opened date_parsed', header: 'OPENED', cell: (ctx) => dateOnly(String(ctx.getValue() ?? '')) },
    { accessorKey: 'issue_category', header: 'ISSUE GROUP', cell: (ctx) => <span className="category-pill">{String(ctx.getValue() || 'Unclassified')}</span> },
    { accessorKey: 'MAKE', header: 'MAKE / MODEL', cell: ({ row }) => <span className="vehicle-cell"><b>{row.original.MAKE}</b><small>{row.original.MODEL}</small></span> },
    { accessorKey: 'BUILD_PLANT_DESC', header: 'BUILD PLANT' },
    { accessorKey: 'CUSTOMER_VERBATIM', header: 'CUSTOMER NARRATIVE', enableSorting: false, cell: ({ row }) => <span className="narrative-cell">{truncate(row.original.CUSTOMER_VERBATIM, 110)}</span> },
  ], [])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [columnsOpen, setColumnsOpen] = useState(false)
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel(), manualPagination: true, manualSorting: true, pageCount: pages, state: { pagination: { pageIndex, pageSize }, sorting, columnVisibility }, onSortingChange: setSorting, onColumnVisibilityChange: setColumnVisibility })
  const downloadFiltered = async () => { const params = new URLSearchParams(); if (debounced) params.set('q', debounced); if (initialCluster) params.set('cluster', initialCluster); for (const [k, v] of Object.entries({ ...filters, category: initialCategory })) if (v) params.set(k, v); try { const response = await fetch(apiUrl(`/api/events/export?${params}`)); if (!response.ok) throw new Error('Export request failed'); const blob = await response.blob(); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'autoinsight-filtered-events.csv'; a.click(); URL.revokeObjectURL(a.href) } catch (e) { setError(String(e)) } }
  const toggleSort = (id: string) => { const current = sorting[0]; setSorting([{ id, desc: current?.id === id ? !current.desc : true }]); setPageIndex(0) }
  return <motion.div className="page-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><div className="explorer-toolbar"><div className="search-box"><Search size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search events, narratives, codes…" aria-label="Search event records" /></div><div className="toolbar-right">{(initialCategory || initialCluster) && <button className="filter-chip" onClick={() => { navigate('/explorer'); setPageIndex(0) }}><Filter size={12} />{initialCategory || `Cluster ${Number(initialCluster) + 1}`}<X size={12} /></button>}<div className="column-control"><button className="secondary-button" onClick={() => setColumnsOpen(!columnsOpen)} aria-expanded={columnsOpen}><SlidersHorizontal size={14} />Columns<ChevronDown size={12} /></button>{columnsOpen && <div className="column-menu">{table.getAllLeafColumns().map((column) => <label key={column.id}><input type="checkbox" checked={column.getIsVisible()} onChange={column.getToggleVisibilityHandler()} /><span>{String(column.columnDef.header)}</span></label>)}</div>}</div><button className="secondary-button" onClick={downloadFiltered} disabled={!total}><Download size={14} />Export filtered</button></div></div>
    <div className="table-card"><div className="table-card-head"><div><b>Quality event records</b><span>{total.toLocaleString()} matching records</span></div><label className="page-size-select">Rows<select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPageIndex(0) }}><option>10</option><option>25</option><option>50</option><option>100</option></select></label></div>{error ? <ErrorState message={error} /> : <div className="table-scroll"><table className="data-table"><thead>{table.getHeaderGroups().map((hg) => <tr key={hg.id}>{hg.headers.map((header) => <th key={header.id}><button className="th-button" onClick={() => header.column.getCanSort() && toggleSort(header.column.id)}>{flexRender(header.column.columnDef.header, header.getContext())}{header.column.getCanSort() && <span className="sort-indicator">{sorting[0]?.id === header.column.id ? sorting[0]?.desc ? '↓' : '↑' : '↕'}</span>}</button></th>)}</tr>)}</thead><tbody>{busy ? <tr><td colSpan={table.getVisibleLeafColumns().length}><div className="table-loading"><span className="spinner" />Loading event records…</div></td></tr> : table.getRowModel().rows.length ? table.getRowModel().rows.map((row) => <tr key={row.id} onClick={() => onSelect(row.original)} className="clickable-row">{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>) : <tr><td colSpan={table.getVisibleLeafColumns().length}><div className="table-empty"><Database size={18} /><b>No matching records</b><span>Adjust search or filters and try again.</span></div></td></tr>}</tbody></table></div>}<div className="table-pagination"><span>Showing {total ? (pageIndex * pageSize + 1).toLocaleString() : 0}–{Math.min((pageIndex + 1) * pageSize, total).toLocaleString()} of {total.toLocaleString()}</span><div><button className="icon-btn" disabled={pageIndex <= 0} onClick={() => setPageIndex((p) => Math.max(0, p - 1))} aria-label="Previous page"><ChevronLeft size={16} /></button><span className="page-number">{pages ? pageIndex + 1 : 0} <i>/</i> {pages}</span><button className="icon-btn" disabled={pageIndex + 1 >= pages} onClick={() => setPageIndex((p) => Math.min(pages - 1, p + 1))} aria-label="Next page"><ChevronRight size={16} /></button></div></div></div></motion.div>
}

function SentimentPage({ count }: { count: number }) {
  const [q, setQ] = useState(''); const [data, setData] = useState<{ rows: Record<string, unknown>[]; total: number; available: boolean } | null>(null)
  useEffect(() => { const t = setTimeout(() => { fetchReviews(q).then(setData).catch(() => setData({ rows: [], total: 0, available: false })) }, 200); return () => clearTimeout(t) }, [q])
  return <motion.div className="page-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><div className="sentiment-status"><div className="sentiment-art"><div className="sentiment-orbit orbit-one" /><div className="sentiment-orbit orbit-two" /><div className="sentiment-core"><Sparkles size={24} /></div><div className="orbit-node node-one" /><div className="orbit-node node-two" /><div className="orbit-node node-three" /></div><div className="sentiment-copy"><span className="eyebrow"><span />COLLECTION STATUS</span><h2>Customer voice, when it's ready.</h2><p>The review analysis workflow is available, but a public review collection was blocked by the source site. AutoInsight stopped collection at the access restriction and has no genuine review records to display.</p><div className="status-facts"><div><span>Collected reviews</span><b>{count.toLocaleString()}</b></div><div><span>Collection status</span><b className="blocked-status"><i />Blocked · HTTP 403</b></div><div><span>Next step</span><b>Authorized export or permitted access</b></div></div><div className="sentiment-actions"><Link to="/reports" className="primary-button">View collection report <ArrowRight size={15} /></Link><span><ShieldCheck size={14} />No sample reviews or synthetic sentiment metrics</span></div></div></div>
    <div className="sentiment-search-card"><div><b>Review explorer</b><span>Search becomes available when genuine reviews are present.</span></div><div className="search-box disabled-search"><Search size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search collected reviews…" aria-label="Search reviews" disabled={!data?.available} /></div></div>
    {data?.available && <div className="review-list">{data.rows.map((r, i) => <article key={String(r['Primary Key'] ?? i)} className="review-card"><b>{String(r.Title ?? 'Untitled review')}</b><p>{String(r['Review Text'] ?? '')}</p><span>{String(r.Sentiment ?? 'Unlabeled')} · {String(r.Rating ?? 'No rating')}</span></article>)}</div>}
  </motion.div>
}

function ReportsPage() {
  const [files, setFiles] = useState<ReportFile[] | null>(null); const [error, setError] = useState('')
  useEffect(() => { fetchReports().then((d) => setFiles(d.files)).catch((e) => setError(String(e))) }, [])
  if (error) return <ErrorState message={error} />
  if (!files) return <LoadingState />
  const pdf = files.filter((f) => f.name.endsWith('.pdf')); const text = files.filter((f) => f.name.endsWith('.md')); const data = files.filter((f) => f.name.endsWith('.csv'))
  return <motion.div className="page-content" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><div className="report-summary"><div className="report-summary-icon"><FileBarChart2 size={20} /></div><div><b>Analysis deliverables</b><p>Generated from the current local project outputs. Downloads reference existing files only.</p></div><span>{files.length} AVAILABLE FILES</span></div>
    <ReportSection title="Stakeholder reports" subtitle="Findings and project status" files={[...pdf, ...text]} /><ReportSection title="Analysis datasets" subtitle="Generated from the supplied source CSV" files={data} />
  </motion.div>
}
function ReportSection({ title, subtitle, files }: { title: string; subtitle: string; files: ReportFile[] }) { return <section className="report-section"><div className="section-heading"><div><h2>{title}</h2><p>{subtitle}</p></div><span className="neutral-chip">{files.length} FILES</span></div><div className="report-grid">{files.map((f) => <article className="report-card" key={f.name}><div className={`report-file-icon ${f.name.endsWith('.pdf') ? 'pdf' : f.name.endsWith('.md') ? 'markdown' : 'csv'}`}>{f.name.endsWith('.pdf') ? <FileBarChart2 size={17} /> : f.name.endsWith('.md') ? <Bookmark size={17} /> : <Database size={17} />}</div><div className="report-card-body"><div className="report-title-row"><h3>{f.name}</h3><span>{f.name.split('.').pop()?.toUpperCase()}</span></div><p>{f.description}</p><div className="report-meta"><span>{formatBytes(f.bytes)}</span><i />{formatDateTime(f.updated)}</div></div><a className="download-button" href={apiUrl(f.path)} download aria-label={`Download ${f.name}`}><Download size={15} /></a></article>)}</div></section> }

function RecentEvents({ rows, onSelect }: { rows: EventRecord[]; onSelect: (r: EventRecord) => void }) { return <section className="recent-card"><div className="section-heading"><div><h2>Recent quality events</h2><p>Latest records by opened date</p></div><Link className="text-link" to="/explorer">Explore all records <ArrowRight size={14} /></Link></div><div className="recent-table-wrap"><table className="recent-table"><thead><tr><th>EVENT ID</th><th>OPENED</th><th>ISSUE CATEGORY</th><th>VEHICLE</th><th>BUILD PLANT</th><th>SUMMARY</th></tr></thead><tbody>{rows.slice(0, 6).map((r) => <tr key={r['Event id']} onClick={() => onSelect(r)}><td className="mono-id">{r['Event id']}</td><td>{dateOnly(r['Opened date_parsed'] ?? r['Opened date'])}</td><td><span className="category-pill">{r.issue_category}</span></td><td><b>{r.MAKE}</b><small className="table-sub">{r.MODEL}</small></td><td>{r.BUILD_PLANT_DESC}</td><td className="recent-summary">{truncate(r.CUSTOMER_VERBATIM, 72)}</td></tr>)}</tbody></table></div></section> }

function EventDrawer({ event, onClose }: { event: EventRecord; onClose: () => void }) { return <><button className="drawer-scrim" onClick={onClose} aria-label="Close event detail" /><motion.aside className="event-drawer" initial={{ x: 560 }} animate={{ x: 0 }} exit={{ x: 560 }} transition={{ duration: .22 }}><div className="drawer-header"><div><span className="eyebrow"><span />SOURCE EVENT</span><h2>{event['Event id']}</h2></div><button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button></div><div className="drawer-scroll"><div className="drawer-meta-grid"><DetailField label="Opened date" value={dateOnly(event['Opened date_parsed'] ?? event['Opened date'])} /><DetailField label="Issue group" value={event.issue_category} /><DetailField label="Vehicle" value={`${event.MAKE} ${event.MODEL}`} /><DetailField label="Build plant" value={event.BUILD_PLANT_DESC} /><DetailField label="Complaint code" value={event.COMPLAINT_CD_DESC} /><DetailField label="Causal code" value={event.CAUSAL_CD_DESC} /></div><Narrative title="Customer verbatim" value={event.CUSTOMER_VERBATIM} /><Narrative title="Causal narrative" value={event.CAUSAL_VERBATIM} /><Narrative title="Correction / repair narrative" value={event.CORRECTION_VERBATIM} /><div className="drawer-tags"><span className="mini-label">MINED TAGS</span><div>{(event.extracted_tags ?? []).length ? event.extracted_tags.map((t) => <span className="tag" key={t}>{t}</span>) : <span className="muted-text">No matching narrative tags</span>}</div></div><div className="drawer-meta-grid detail-derived"><DetailField label="Failure components" value={(event['Failure Component_parsed'] ?? []).join(', ') || 'Not recorded'} /><DetailField label="Failure conditions" value={(event['Failure Condition_parsed'] ?? []).join(', ') || 'Not recorded'} /><DetailField label="Corrective action" value={(event['Fix Condition_parsed'] ?? []).join(', ') || 'Not recorded'} /><DetailField label="Text cluster" value={event.text_cluster == null || event.text_cluster === '' ? 'Unassigned' : `Cluster ${Number(event.text_cluster) + 1}`} /></div><div className="source-note"><ShieldCheck size={14} />Source fields and derived fields are shown separately.</div></div></motion.aside></> }
function DetailField({ label, value }: { label: string; value: string }) { return <div className="detail-field"><span>{label}</span><b>{value || 'Not recorded'}</b></div> }
function Narrative({ title, value }: { title: string; value: string }) { return <div className="narrative-block"><span className="mini-label">{title}</span><p>{value || 'No source narrative recorded.'}</p></div> }

function MetricCard({ label, value, detail, icon: Icon, accent, hint }: { label: string; value: string; detail: string; icon: LucideIcon; accent: string; hint?: string }) { return <div className={`metric-card accent-${accent}`}><div className="metric-top"><span>{label}</span><div className="metric-icon"><Icon size={16} /></div></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div>{hint && <div className="metric-hint" title={hint}><AlertTriangle size={12} />Sparse annotations</div>}</div> }
function ChartPanel({ title, subtitle, badge, className = '', children }: { title: string; subtitle: string; badge?: string; className?: string; children: React.ReactNode }) { return <article className={`chart-panel ${className}`}><div className="chart-panel-head"><div><h2>{title}</h2><p>{subtitle}</p></div>{badge && <span className="chart-badge">{badge}</span>}</div>{children}</article> }
function HorizontalBars({ data, color, empty, onClick }: { data: { label: string; count: number }[]; color: string; empty?: string; onClick?: (label: string) => void }) { if (!data.length) return <div className="chart-empty"><Database size={18} /><span>{empty || 'No records available for this view.'}</span></div>; const max = Math.max(...data.map((x) => x.count), 1); return <div className="hbar-list">{data.slice(0, 10).map((d) => <button key={d.label} className={`hbar-row ${onClick ? 'hbar-row--clickable' : ''}`} onClick={() => onClick?.(d.label)} title={onClick ? `Filter by ${d.label}` : d.label}><span className="hbar-label">{d.label}</span><span className="hbar-track"><i style={{ width: `${Math.max(d.count / max * 100, 2)}%`, background: color }} /></span><b>{d.count.toLocaleString()}</b></button>)}</div> }
function ChartTooltip({ active, payload, label, suffix }: { active?: boolean; payload?: { name?: string; value?: number; payload?: { label?: string } }[]; label?: string; suffix?: string }) { if (!active || !payload?.length) return null; return <div className="chart-tooltip"><span>{payload[0]?.payload?.label ?? label}</span><b>{Number(payload[0]?.value ?? 0).toLocaleString()} {suffix}</b></div> }
function LoadingState() { return <div className="loading-state"><span className="spinner" /><b>Loading quality signals</b><span>Reading current project outputs…</span></div> }
function ErrorState({ message = 'Unable to load the local analysis outputs.' }: { message?: string }) { return <div className="error-state"><div><AlertTriangle size={18} /></div><b>Data is unavailable</b><span>{message}</span><small>Run the Task 2 pipeline and start the local API to restore the dashboard.</small></div> }

function pct(value: number, total: number) { return total ? (value / total * 100).toFixed(1) : '0.0' }
function truncate(value: unknown, max = 120) { const text = String(value ?? '').replace(/\s+/g, ' ').trim(); return text.length > max ? `${text.slice(0, max - 1)}…` : text || 'No narrative recorded' }
function dateOnly(value: string) { if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.valueOf()) ? value : new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: 'short', day: '2-digit', timeZone: 'UTC' }).format(d) }
function formatDateTime(value: string) { return new Intl.DateTimeFormat('en-CA', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function formatRelative(value: string) { const mins = Math.max(0, Math.round((Date.now() - new Date(value).valueOf()) / 60000)); return mins < 1 ? 'just now' : mins < 60 ? `${mins}m ago` : `${Math.floor(mins / 60)}h ago` }
function formatBytes(value: number) { return value > 1024 * 1024 ? `${(value / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(value / 1024))} KB` }

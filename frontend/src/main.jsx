import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, ArrowLeft, BarChart3, CalendarClock, Check, ChevronRight, CirclePlus, LayoutList, RefreshCw, UserRound } from 'lucide-react'
import './styles.css'

const API = 'http://127.0.0.1:8000'
const statuses = ['new', 'contacted', 'interested', 'follow_up', 'applied', 'converted', 'lost']
const allowedTransitions = { new: ['contacted', 'lost'], contacted: ['interested', 'follow_up', 'lost'], interested: ['follow_up', 'applied', 'lost'], follow_up: ['interested', 'applied', 'lost'], applied: ['converted', 'lost'], converted: [], lost: ['contacted'] }
const sources = [{ id: 1, name: 'Website' }, { id: 2, name: 'Walk-in' }, { id: 3, name: 'Phone call' }, { id: 4, name: 'WhatsApp' }, { id: 5, name: 'Education fair' }, { id: 6, name: 'Campaign' }]

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Request failed')
  }
  return response.json()
}

function App() {
  const [screen, setScreen] = useState('leads')
  const [leads, setLeads] = useState([])
  const [selected, setSelected] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [counsellors, setCounsellors] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [counsellorFilter, setCounsellorFilter] = useState('')
  const [error, setError] = useState('')

  const loadLeads = () => { const params = new URLSearchParams(); if (statusFilter) params.set('status', statusFilter); if (sourceFilter) params.set('source_id', sourceFilter); if (counsellorFilter) params.set('assigned_to', counsellorFilter); return api(`/leads${params.toString() ? `?${params}` : ''}`).then((items) => { setLeads(items); return items }).catch((e) => { setError(e.message); return [] }) }
  useEffect(() => { loadLeads(); api('/leads/counsellors').then(setCounsellors).catch(() => {}) }, [statusFilter, sourceFilter, counsellorFilter])
  useEffect(() => { if (screen === 'dashboard') api('/dashboard').then(setDashboard).catch((e) => setError(e.message)) }, [screen])

  const openLead = (lead) => { setSelected(lead); setScreen('detail') }
  const refresh = async () => { const items = await loadLeads(); if (selected) { const updated = items.find((item) => item.id === selected.id); if (updated) setSelected(updated) } if (screen === 'dashboard') api('/dashboard').then(setDashboard) }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">LM</span><span>Lead Manager</span></div>
        <p className="eyebrow">Admissions desk</p>
        <nav>
          <button className={screen === 'leads' || screen === 'detail' ? 'active' : ''} onClick={() => setScreen('leads')}><LayoutList size={17} /> Leads</button>
          <button className={screen === 'dashboard' ? 'active' : ''} onClick={() => setScreen('dashboard')}><BarChart3 size={17} /> Manager dashboard</button>
        </nav>
        <div className="sidebar-note"><span className="live-dot" /> API connected<br /><small>Local workspace</small></div>
      </aside>
      <main className="main">
        <header className="topbar"><div><p className="eyebrow">Lead operations / 24 Sep 2026</p><h1>{screen === 'dashboard' ? 'Manager dashboard' : screen === 'detail' ? 'Lead detail' : 'All leads'}</h1></div><button className="icon-button" title="Refresh" onClick={refresh}><RefreshCw size={18} /></button></header>
        {error && <div className="notice error">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
        {screen === 'dashboard' ? <Dashboard data={dashboard} /> : screen === 'detail' ? <Detail lead={selected} counsellors={counsellors} onBack={() => setScreen('leads')} onChanged={refresh} /> : <LeadList leads={leads} statusFilter={statusFilter} setStatusFilter={setStatusFilter} sourceFilter={sourceFilter} setSourceFilter={setSourceFilter} counsellorFilter={counsellorFilter} setCounsellorFilter={setCounsellorFilter} counsellors={counsellors} onOpen={openLead} onCreated={refresh} />}
      </main>
    </div>
  )
}

function LeadList({ leads, statusFilter, setStatusFilter, sourceFilter, setSourceFilter, counsellorFilter, setCounsellorFilter, counsellors, onOpen, onCreated }) {
  const [showForm, setShowForm] = useState(false)
  const [page, setPage] = useState(1)
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil(leads.length / pageSize))
  const visibleLeads = leads.slice((page - 1) * pageSize, page * pageSize)
  useEffect(() => { setPage(1) }, [leads, statusFilter])
  return <>
    <section className="metric-row"><Metric label="Visible leads" value={leads.length} /><Metric label="Open pipeline" value={leads.filter((lead) => !['converted', 'lost'].includes(lead.status)).length} tone="mint" /><Metric label="Needs attention" value={leads.filter((lead) => lead.status === 'follow_up').length} tone="amber" /></section>
    <section className="toolbar"><div className="filter-label">Filter leads</div><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">All statuses</option>{statuses.map((status) => <option key={status}>{status}</option>)}</select><select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}><option value="">All sources</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}</select><select value={counsellorFilter} onChange={(e) => setCounsellorFilter(e.target.value)}><option value="">All counsellors</option>{counsellors.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select><button className="primary" onClick={() => setShowForm(!showForm)}><CirclePlus size={17} /> Add lead</button></section>
    {showForm && <LeadForm onCreated={() => { setShowForm(false); onCreated() }} />}
    <section className="table-wrap"><div className="table-head"><span>Lead</span><span>Status</span><span>Assigned</span><span>Last activity</span><span /></div>{visibleLeads.map((lead) => <button className="lead-row" key={lead.id} onClick={() => onOpen(lead)}><span><strong>{lead.name}</strong><small>{lead.phone} · {lead.email || 'No email'}</small></span><span><Status status={lead.status} /></span><span className="muted">Counsellor #{lead.assigned_to || '—'}</span><span className="muted">{formatDate(lead.last_activity_at)}</span><ChevronRight size={17} className="muted" /></button>)}{!leads.length && <div className="empty">No leads match this filter.</div>}{leads.length > 0 && <Pagination page={page} totalPages={totalPages} totalItems={leads.length} onPage={setPage} />}</section>
  </>
}

function LeadForm({ onCreated }) {
  const [form, setForm] = useState({ name: '', phone: '', email: '', source_id: 1 })
  const [message, setMessage] = useState('')
  const submit = async (event) => { event.preventDefault(); try { const result = await api('/leads', { method: 'POST', body: JSON.stringify({ ...form, source_id: Number(form.source_id), courses: [] }) }); setMessage(result.duplicate ? 'Duplicate phone found; existing lead returned.' : 'Lead created.'); onCreated() } catch (error) { setMessage(error.message) } }
  return <form className="form-panel" onSubmit={submit}><div className="section-title">New lead <small>Basic contact record</small></div><div className="form-grid"><label>Name<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label>Phone<input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label><label>Email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>Source<select value={form.source_id} onChange={(e) => setForm({ ...form, source_id: e.target.value })}><option value="1">Website</option><option value="2">Walk-in</option><option value="3">Phone call</option><option value="4">WhatsApp</option></select></label></div><div className="form-actions"><span className="muted">{message}</span><button className="primary" type="submit">Save lead</button></div></form>
}

function Detail({ lead, counsellors, onBack, onChanged }) {
  const [activities, setActivities] = useState([]); const [followUps, setFollowUps] = useState([]); const [newStatus, setNewStatus] = useState(lead?.status || 'new'); const [follow, setFollow] = useState({ due_at: '', type: 'call', note: '' }); const [message, setMessage] = useState('')
  useEffect(() => { if (lead) { api(`/leads/${lead.id}/activities`).then(setActivities); api(`/leads/${lead.id}/follow-ups`).then(setFollowUps) } }, [lead])
  useEffect(() => { if (lead) setNewStatus(lead.status) }, [lead])
  if (!lead) return <div className="empty">Choose a lead first.</div>
  const nextStatuses = statuses.map((status) => ({
    status,
    disabled: status !== lead.status && !(allowedTransitions[lead.status] || []).includes(status),
  }))
  const changeStatus = async () => { try { await api(`/leads/${lead.id}/status`, { method: 'PATCH', body: JSON.stringify({ status: newStatus, lost_reason: newStatus === 'lost' ? 'No response' : null }) }); setMessage('Status updated'); onChanged() } catch (error) { setMessage(error.message) } }
  const assign = async (event) => { try { await api(`/leads/${lead.id}/reassign`, { method: 'PATCH', body: JSON.stringify({ counsellor_id: Number(event.target.value) }) }); setMessage('Reassigned'); onChanged() } catch (error) { setMessage(error.message) } }
  const addFollowUp = async (event) => { event.preventDefault(); try { const item = await api(`/leads/${lead.id}/follow-ups`, { method: 'POST', body: JSON.stringify({ ...follow, due_at: new Date(follow.due_at).toISOString() }) }); setFollowUps([...followUps, item]); setFollow({ due_at: '', type: 'call', note: '' }); setMessage('Follow-up added') } catch (error) { setMessage(error.message) } }
  const closeFollowUp = async (id, status) => { const item = await api(`/follow-ups/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }); setFollowUps(followUps.map((followUp) => followUp.id === id ? item : followUp)) }
  const remove = async () => { if (!window.confirm(`Delete ${lead.name}? This also removes its follow-ups and activity history.`)) return; try { await api(`/leads/${lead.id}`, { method: 'DELETE' }); onBack(); onChanged() } catch (error) { setMessage(error.message) } }
  return <><button className="back-button" onClick={onBack}><ArrowLeft size={16} /> Back to leads</button><section className="detail-grid"><div><div className="detail-hero"><div className="avatar">{lead.name.slice(0, 1)}</div><div><p className="eyebrow">Lead #{lead.id}</p><h2>{lead.name}</h2><p className="muted">{lead.phone} · {lead.email || 'No email provided'}</p></div><Status status={lead.status} /></div><div className="panel"><div className="section-title">Status <small>Next: {(allowedTransitions[lead.status] || []).join(', ') || 'no further transitions'}{message ? ` · ${message}` : ''}</small></div><div className="inline-form"><select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>{nextStatuses.map(({ status, disabled }) => <option disabled={disabled} key={status}>{status}</option>)}</select><button className="primary" disabled={newStatus === lead.status} onClick={changeStatus}><Check size={16} /> Update</button></div></div><div className="panel"><div className="section-title">Follow-ups</div>{followUps.map((item) => <div className="follow-row" key={item.id}><CalendarClock size={17} /><span><strong>{item.type}</strong><small>{item.note || 'No note'} · {formatDate(item.due_at)}</small></span><Status status={item.status} />{item.status === 'pending' && <button className="text-button" onClick={() => closeFollowUp(item.id, 'done')}>Done</button>}</div>)}<form className="follow-form" onSubmit={addFollowUp}><input required type="datetime-local" value={follow.due_at} onChange={(e) => setFollow({ ...follow, due_at: e.target.value })} /><select value={follow.type} onChange={(e) => setFollow({ ...follow, type: e.target.value })}><option>call</option><option>whatsapp</option><option>visit</option><option>email</option></select><input placeholder="Note" value={follow.note} onChange={(e) => setFollow({ ...follow, note: e.target.value })} /><button className="primary" type="submit">Add</button></form></div></div><aside><div className="panel"><div className="section-title">Assignment</div><select value={lead.assigned_to || ''} onChange={assign}><option value="">Unassigned</option>{counsellors.filter((person) => person.is_active).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></div><div className="panel"><div className="section-title">Activity timeline</div><div className="timeline">{activities.map((item) => <div className="timeline-item" key={item.id}><span /><div><strong>{item.action.replaceAll('_', ' ')}</strong><small>{item.new_value || item.old_value || 'System event'} · {formatDate(item.created_at)}</small></div></div>)}</div></div><div className="panel danger-panel"><button className="danger-button" onClick={remove}>Delete lead</button><small>This permanently removes the lead and related history.</small></div></aside></section></>
}

function Dashboard({ data }) {
  const [statusPage, setStatusPage] = useState(1)
  const statusEntries = data ? Object.entries(data.by_status) : []
  const statusPageSize = 5
  const statusPages = Math.max(1, Math.ceil(statusEntries.length / statusPageSize))
  const visibleStatuses = statusEntries.slice((statusPage - 1) * statusPageSize, statusPage * statusPageSize)
  useEffect(() => { setStatusPage(1) }, [data])
  if (!data) return <div className="empty">Loading dashboard…</div>
  return <><section className="metric-row"><Metric label="Total leads" value={data.total_leads} /><Metric label="Overdue follow-ups" value={data.overdue_follow_ups.length} tone="red" /><Metric label="Stale leads" value={data.stale_leads.length} tone="amber" /></section><section className="dashboard-grid"><div className="panel"><div className="section-title">Status table <small>{statusEntries.length} statuses</small></div><div className="status-table"><div className="status-table-head"><span>Status</span><span>Leads</span></div>{visibleStatuses.map(([key, value]) => <div className="status-table-row" key={key}><Status status={key} /><strong>{value}</strong></div>)}</div><Pagination page={statusPage} totalPages={statusPages} totalItems={statusEntries.length} onPage={setStatusPage} /></div><div className="panel"><div className="section-title">Ageing</div>{Object.entries(data.ageing).map(([key, value]) => <div className="bar-row" key={key}><span>{key} days</span><div><i className="amber-bar" style={{ width: `${Math.max(5, value / Math.max(data.total_leads, 1) * 100)}%` }} /></div><strong>{value}</strong></div>)}</div><div className="panel"><div className="section-title">By source</div>{Object.entries(data.by_source).map(([key, value]) => <div className="insight-row" key={key}><span>{key}</span><strong>{value}</strong></div>)}</div><div className="panel"><div className="section-title">By counsellor</div>{Object.entries(data.by_counsellor).map(([key, value]) => <div className="insight-row" key={key}><span>{key}</span><strong>{value}</strong></div>)}</div><div className="panel wide"><div className="section-title">Counsellor conversion</div>{Object.entries(data.conversion_rate_by_counsellor).map(([key, value]) => <div className="conversion-row" key={key}><UserRound size={16} /><span>{key}</span><strong>{value}%</strong></div>)}</div><div className="panel"><div className="section-title">Overdue follow-ups</div>{data.overdue_follow_ups.length ? data.overdue_follow_ups.map((item) => <div className="insight-row" key={item.id}><span>Lead #{item.lead_id} · {item.type}<small>{formatDate(item.due_at)}</small></span><Status status={item.status} /></div>) : <p className="muted">No overdue follow-ups.</p>}</div><div className="panel"><div className="section-title">Stale leads</div>{data.stale_leads.length ? data.stale_leads.slice(0, 8).map((lead) => <div className="insight-row" key={lead.id}><span>{lead.name}<small>Last active {formatDate(lead.last_activity_at)}</small></span><Status status={lead.status} /></div>) : <p className="muted">No stale leads.</p>}</div></section></>
}
function Pagination({ page, totalPages, totalItems, onPage }) { return <div className="pagination"><span>{totalItems} total · page {page} of {totalPages}</span><div><button className="page-button" disabled={page === 1} onClick={() => onPage(page - 1)}>Previous</button><button className="page-button" disabled={page === totalPages} onClick={() => onPage(page + 1)}>Next</button></div></div> }
function Metric({ label, value, tone = '' }) { return <div className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong></div> }
function Status({ status }) { return <span className={`status ${status}`}>{status?.replaceAll('_', ' ')}</span> }
function formatDate(value) { return value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '—' }

export default App

createRoot(document.getElementById('root')).render(<App />)
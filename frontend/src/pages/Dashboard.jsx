import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { getStats } from '../api/applications'

const STATUS_COLORS = {
  Applied:       '#6366f1',
  OA:            '#a855f7',
  'Phone Screen':'#06b6d4',
  Interview:     '#f59e0b',
  Offer:         '#22c55e',
  Rejected:      '#ef4444',
  Ghosted:       '#9ca3af',
}

const WORK_TYPE_COLORS = {
  Remote: '#6366f1',
  Hybrid: '#f59e0b',
  Onsite: '#22c55e',
}

const PLATFORM_COLORS = [
  '#6366f1','#a855f7','#06b6d4','#f59e0b','#22c55e','#ef4444',
]

function StatCard({ label, value, sub, color = 'text-gray-900' }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function ChartCard({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm font-semibold text-gray-700 mb-4">{title}</p>
      {children}
    </div>
  )
}

const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null
  const RADIAN = Math.PI / 180
  const r = innerRadius + (outerRadius - innerRadius) * 0.6
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getStats().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <p className="p-8 text-red-600">{error}</p>
  if (!data) return <p className="p-8 text-gray-400">Loading…</p>
  if (data.total === 0) return (
    <div className="max-w-2xl mx-auto mt-20 text-center text-gray-400">
      <p className="text-lg">No applications yet.</p>
      <p className="text-sm mt-1">Add some applications to see your stats.</p>
    </div>
  )

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Applied" value={data.total} />
        <StatCard label="Response Rate" value={`${data.response_rate}%`}
          sub="OA / Screen / Interview / Offer / Rejected"
          color={data.response_rate >= 20 ? 'text-green-600' : 'text-gray-900'} />
        <StatCard label="Interviews" value={data.interviews}
          color={data.interviews > 0 ? 'text-amber-600' : 'text-gray-900'} />
        <StatCard label="Offers" value={data.offers}
          color={data.offers > 0 ? 'text-green-600' : 'text-gray-900'} />
      </div>

      {/* Status donut + Weekly bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard title="Status Breakdown">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data.by_status}
                cx="50%" cy="50%"
                innerRadius={60} outerRadius={100}
                dataKey="value"
                labelLine={false}
                label={renderCustomLabel}
              >
                {data.by_status.map((entry) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#9ca3af'} />
                ))}
              </Pie>
              <Tooltip formatter={(v, n) => [v, n]} />
              <Legend iconType="circle" iconSize={10} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Applications per Week (last 12 weeks)">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.by_week} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} interval={1} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" name="Applications" fill="#6366f1" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Platform + Work type */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.by_platform.length > 0 && (
          <ChartCard title="Platform">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={data.by_platform}
                  cx="50%" cy="50%"
                  outerRadius={85}
                  dataKey="value"
                  labelLine={false}
                  label={renderCustomLabel}
                >
                  {data.by_platform.map((_, i) => (
                    <Cell key={i} fill={PLATFORM_COLORS[i % PLATFORM_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" iconSize={10} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {data.by_work_type.length > 0 && (
          <ChartCard title="Work Type">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={data.by_work_type}
                  cx="50%" cy="50%"
                  outerRadius={85}
                  dataKey="value"
                  labelLine={false}
                  label={renderCustomLabel}
                >
                  {data.by_work_type.map((entry) => (
                    <Cell key={entry.name} fill={WORK_TYPE_COLORS[entry.name] ?? '#9ca3af'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" iconSize={10} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}
      </div>
    </div>
  )
}

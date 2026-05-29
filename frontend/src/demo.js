export const DEMO_KEY = 'jc_demo'
export const isDemoMode = () => localStorage.getItem(DEMO_KEY) === 'true'
export const enterDemo = () => localStorage.setItem(DEMO_KEY, 'true')
export const exitDemo = () => localStorage.removeItem(DEMO_KEY)

export const DEMO_APPS = [
  {
    id: 1, company: 'Anthropic', title: 'Research Engineer, Interpretability',
    location: 'San Francisco, CA', salary_min: 180000, salary_max: 250000,
    work_type: 'Hybrid', platform: 'Greenhouse', status: 'Interview',
    applied_date: '2026-05-10', source_url: null, created_at: '2026-05-10T10:00:00',
  },
  {
    id: 2, company: 'Waymo', title: 'Data Scientist, Perception',
    location: 'Mountain View, CA', salary_min: 160000, salary_max: 220000,
    work_type: 'Onsite', platform: 'LinkedIn', status: 'Phone Screen',
    applied_date: '2026-05-08', source_url: null, created_at: '2026-05-08T10:00:00',
  },
  {
    id: 3, company: 'Stripe', title: 'Machine Learning Engineer',
    location: 'Remote', salary_min: 170000, salary_max: 230000,
    work_type: 'Remote', platform: 'Company Site', status: 'OA',
    applied_date: '2026-05-05', source_url: null, created_at: '2026-05-05T10:00:00',
  },
  {
    id: 4, company: 'Duolingo', title: 'Senior Data Scientist',
    location: 'Pittsburgh, PA', salary_min: 150000, salary_max: 200000,
    work_type: 'Hybrid', platform: 'Greenhouse', status: 'Applied',
    applied_date: '2026-05-14', source_url: null, created_at: '2026-05-14T10:00:00',
  },
  {
    id: 5, company: 'Netflix', title: 'Data Scientist, Recommendations',
    location: 'Los Gatos, CA', salary_min: 200000, salary_max: 300000,
    work_type: 'Onsite', platform: 'Lever', status: 'Rejected',
    applied_date: '2026-04-28', source_url: null, created_at: '2026-04-28T10:00:00',
  },
  {
    id: 6, company: 'Notion', title: 'ML Engineer, Search',
    location: 'San Francisco, CA', salary_min: 160000, salary_max: 210000,
    work_type: 'Hybrid', platform: 'Ashby', status: 'Ghosted',
    applied_date: '2026-04-20', source_url: null, created_at: '2026-04-20T10:00:00',
  },
]

export const DEMO_STATS = {
  total: DEMO_APPS.length,
  offers: 0,
  interviews: 1,
  response_rate: 66.7,
  by_status: [
    { name: 'Applied', value: 1 },
    { name: 'OA', value: 1 },
    { name: 'Phone Screen', value: 1 },
    { name: 'Interview', value: 1 },
    { name: 'Rejected', value: 1 },
    { name: 'Ghosted', value: 1 },
  ],
  by_week: [
    ...Array.from({ length: 8 }, (_, i) => ({ week: `0${i + 1}/01`, count: 0 })),
    { week: '04/20', count: 1 },
    { week: '04/27', count: 1 },
    { week: '05/04', count: 2 },
    { week: '05/11', count: 2 },
  ],
  by_platform: [
    { name: 'Greenhouse', value: 2 },
    { name: 'LinkedIn', value: 1 },
    { name: 'Lever', value: 1 },
    { name: 'Company Site', value: 1 },
    { name: 'Ashby', value: 1 },
  ],
  by_work_type: [
    { name: 'Hybrid', value: 3 },
    { name: 'Onsite', value: 2 },
    { name: 'Remote', value: 1 },
  ],
}

import { STORAGE_KEY } from '../constants';
import type { Opportunity } from '../types/opportunity';

interface StorageResult {
  data: Opportunity[];
  isNew: boolean;
}

export class StorageError extends Error {
  constructor(message: string, public readonly operation: 'read' | 'write') {
    super(message);
    this.name = 'StorageError';
  }
}

function getStorage(): { get: (key: string) => string | null; set: (key: string, value: string) => void } | null {
  if (typeof window !== 'undefined') {
    if (window.storage && typeof window.storage.get === 'function') {
      return window.storage;
    }
    if (window.localStorage) {
      return {
        get: (key: string) => window.localStorage.getItem(key),
        set: (key: string, value: string) => window.localStorage.setItem(key, value),
      };
    }
  }
  return null;
}

const SEED_DATA: Opportunity[] = [
  {
    id: 'seed_001',
    title: 'Emerging Technologies Hackathon',
    type: 'Hackathon',
    source: 'TCOE India',
    link: 'https://hackathon2026.tcoe.in',
    deadline: '2026-07-31',
    eligibility: 'UG/PG students. Teams of 1-5. 3rd year eligible.',
    tags: ['AI/ML', 'Cybersecurity', '5G/6G', 'Quantum'],
    status: 'Not Started',
    notes: 'Govt of India hackathon. ₹10L+ prize pool. FREE registration.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_002',
    title: 'MIT India National Hackathon',
    type: 'Hackathon',
    source: 'MIT India',
    link: 'https://punehackathon.mitindia.com',
    deadline: '2026-08-09',
    eligibility: 'Teams of 4. Engineering/Science/Management/Design streams. 3rd year eligible.',
    tags: ['Full Stack', 'Innovation', 'AI'],
    status: 'Not Started',
    notes: 'Pune qualifier Aug 21-22. Grand finale Delhi Oct 24. ₹25L prize pool. ₹4K/team fee.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_003',
    title: 'DRDO DMRL Hyderabad Paid Internship',
    type: 'Internship',
    source: 'DRDO DMRL',
    link: '',
    deadline: '2026-07-15',
    eligibility: 'Final year BE/BTech/ME/MTech. Min CGPA 7.0. Below 28. Indian national.',
    tags: ['ECE', 'CSE', 'ME', 'Materials'],
    status: 'Applied',
    notes: 'Hyderabad (Kanchanbagh). ₹5K/month for 6 months. Email to hrd.dmrl@gov.in with subject "Application for paid internship 2026, DMRL Hyderabad"',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_004',
    title: 'IET India Scholarship Award 2026',
    type: 'Certification',
    source: 'IET India',
    link: 'https://scholarships.theietevents.com',
    deadline: '2026-07-15',
    eligibility: 'All 1st-4th year UG engineering. Min 60% or 6.0 CGPA. No backlogs.',
    tags: ['Scholarship', 'Leadership', 'All Branches'],
    status: 'Applied',
    notes: '₹10L total prize pool. Online test → Regional rounds → National finals Bengaluru Sep 2026. Most prestigious UG engineering scholarship in India.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_005',
    title: 'What The Tech Hackathon Hyderabad',
    type: 'Hackathon',
    source: 'Founders Fest',
    link: 'https://hackathon.foundersfest.org',
    deadline: '2026-08-06',
    eligibility: 'Students. 3500+ participants expected.',
    tags: ['Full Stack', 'General', 'Hyderabad'],
    status: 'Not Started',
    notes: 'GMC Balayogi Indoor Stadium, Gachibowli. 36-hour hackathon. ₹299 entry fee. Aug 6-7.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_006',
    title: 'Google SWE Intern Summer 2026',
    type: 'Internship',
    source: 'Google',
    link: 'https://www.google.com/about/careers/applications/internships',
    deadline: '2026-08-15',
    eligibility: 'B.Tech CS or related. Strong DSA. Java/C++/Python/Go.',
    tags: ['SWE', 'DSA', 'Top Tier'],
    status: 'Not Started',
    notes: '₹80K-1.6L/month. Hyderabad location. 12+ weeks. Rolling applications — apply ASAP.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_007',
    title: 'Salesforce SWE Intern Hyderabad',
    type: 'Internship',
    source: 'Salesforce',
    link: 'https://careers.salesforce.com',
    deadline: '2026-08-15',
    eligibility: 'B.Tech/B.E in CS. 2026/2027 graduation. Java/JS/Python. DSA proficiency.',
    tags: ['SWE', 'CRM', 'Hyderabad', 'Top Tier'],
    status: 'Not Started',
    notes: 'Hyderabad Hi-Tech City. ₹80K-1.2L/month. PPO rate 50-70%. Fully furnished housing + meals + shuttle included.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_008',
    title: 'Goldman Sachs Summer Analyst 2026',
    type: 'Internship',
    source: 'Goldman Sachs',
    link: 'https://www.goldmansachs.com/careers/students/programs-and-internships',
    deadline: '2026-08-20',
    eligibility: 'Pre-final year (2027 graduating). Strong analytical skills. Python/Java/C++.',
    tags: ['Finance', 'SWE', 'Hyderabad', 'Top Tier'],
    status: 'Not Started',
    notes: 'Hyderabad & Bengaluru locations. 9-10 weeks. Summer 2026 (May-Jul). One of highest-paying internships.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_009',
    title: 'Generation Google Scholarship APAC 2026',
    type: 'Certification',
    source: 'Google',
    link: 'https://www.google.com/about/careers/applications/buildyourfuture/scholarships',
    deadline: '2026-08-31',
    eligibility: 'Women in CS/engineering. 2nd/3rd year UG. Min 3.5 CGPA. Financial need.',
    tags: ['Scholarship', 'Women in Tech', 'Google'],
    status: 'Not Started',
    notes: '$2,500 USD (~₹2.1L) one-time scholarship. Apply before Aug 31. [If not eligible, skip this entry].',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_010',
    title: 'GitHub Student Developer Pack',
    type: 'Certification',
    source: 'GitHub',
    link: 'https://education.github.com/pack',
    deadline: '2026-12-31',
    eligibility: 'Age 13+. Enrolled in degree program. Student email or ID required.',
    tags: ['Free', 'Developer Tools', 'Copilot', 'Essential'],
    status: 'Not Started',
    notes: 'FREE — GitHub Pro, Copilot Pro, JetBrains IDEs, Canva Pro, $200 DigitalOcean credits, $200 MongoDB Atlas. Apply NOW — instant approval.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_011',
    title: 'AWS Educate Free Certification Vouchers',
    type: 'Certification',
    source: 'AWS',
    link: 'https://aws.amazon.com/education/awseducate',
    deadline: '2026-12-31',
    eligibility: 'All students. Complete SkillBuilder courses + practice exams to earn vouchers.',
    tags: ['Cloud', 'AWS', 'Free', 'Certification'],
    status: 'Not Started',
    notes: 'FREE exam vouchers for Cloud Practitioner, Solutions Architect, Developer, SysOps, ML Engineer. Earn points through courses. 100% free foundational level.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_012',
    title: 'Google Cloud Digital Leader Bootcamp',
    type: 'Certification',
    source: 'Google Cloud',
    link: 'https://rsvp.withgoogle.com/events/cdl-certification-bootcamp-june-online/home',
    deadline: '2026-08-30',
    eligibility: 'Age 18+. No cloud experience required.',
    tags: ['Cloud', 'Google', 'Free', 'Certification'],
    status: 'Not Started',
    notes: 'FREE official Google Cloud certification. 1-day intensive bootcamp. Exam voucher included. Highly valued on resume.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_013',
    title: 'GSSoC 2026 — Open Source Contribution',
    type: 'Certification',
    source: 'GirlScript Foundation',
    link: 'https://gssoc.girlscript.org',
    deadline: '2026-08-14',
    eligibility: 'Anyone worldwide. Any skill level. Completely free.',
    tags: ['Open Source', 'AI', 'Free'],
    status: 'Not Started',
    notes: 'Opensource Track + Agents for India AI Track. Cash prizes up to ₹50K. Certificates, LORs, swag. Active now — contributions ongoing.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_014',
    title: 'Digital India Hackathon 2026',
    type: 'Hackathon',
    source: 'SNIST Hyderabad',
    link: 'https://internshala.com/competitions/digital-india-hackathon-2026',
    deadline: '2026-07-10',
    eligibility: 'UG/PG engineering students.',
    tags: ['Digital India', 'Hyderabad', 'AI/ML'],
    status: 'Completed',
    notes: 'Sreenidhi Institute, Hyderabad. 24-hour offline hackathon Jul 10-11. ₹2.5L prize pool. Registration closed.',
    date_added: '2026-07-25',
  },
  {
    id: 'seed_015',
    title: 'Oracle Race to Certification 2025',
    type: 'Certification',
    source: 'Oracle',
    link: 'https://education.oracle.com/race-to-certification-2025',
    deadline: '2026-10-31',
    eligibility: 'All students. No prerequisites for foundational tracks.',
    tags: ['Cloud', 'Oracle', 'Free', 'AI', 'Database'],
    status: 'Not Started',
    notes: 'FREE training + free exam vouchers. 22 certification tracks: AI, Cloud, Data Platform, APEX. Multiple free exam attempts. Very high value.',
    date_added: '2026-07-25',
  },
];

export function loadOpportunities(): StorageResult {
  const storage = getStorage();

  if (!storage) {
    return { data: [], isNew: true };
  }

  try {
    const raw = storage.get(STORAGE_KEY);
    if (raw === null || raw === undefined) {
      storage.set(STORAGE_KEY, JSON.stringify(SEED_DATA));
      return { data: SEED_DATA, isNew: true };
    }
    const parsed = JSON.parse(raw) as Opportunity[];
    if (!Array.isArray(parsed)) {
      throw new Error('Stored data is not an array');
    }
    return { data: parsed, isNew: false };
  } catch (e) {
    throw new StorageError(
      `Failed to load opportunities: ${e instanceof Error ? e.message : 'Unknown error'}`,
      'read'
    );
  }
}

export function saveOpportunities(list: Opportunity[]): void {
  const storage = getStorage();

  if (!storage) {
    throw new StorageError('Storage API not available', 'write');
  }

  try {
    storage.set(STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    throw new StorageError(
      `Failed to save opportunities: ${e instanceof Error ? e.message : 'Unknown error'}`,
      'write'
    );
  }
}

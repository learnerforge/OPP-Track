export interface Opportunity {
  id: string;
  user_id: string;
  title: string;
  type: OpportunityType;
  source: string;
  link: string;
  deadline: string; // ISO date YYYY-MM-DD
  eligibility: string;
  tags: string[];
  status: OpportunityStatus;
  notes: string;
  date_added: string; // ISO date YYYY-MM-DD
  location?: string | null;
  prize_pool?: string | null;
  participants?: string | null;
  organizer?: string | null;
  duration?: string | null;
  quality_score?: number | null;
}

export type OpportunityType =
  | 'Hackathon'
  | 'Internship'
  | 'Certification'
  | 'Competition';

export type OpportunityStatus =
  | 'Not Started'
  | 'Applied'
  | 'In Progress'
  | 'Rejected'
  | 'Completed';

export type UrgencyTier = 'critical' | 'warning' | 'safe' | 'expired';

export type SortKey = 'deadline' | 'date_added' | 'title';

export type SortDir = 'asc' | 'desc';

export type ViewMode = 'dashboard' | 'weekly-review' | 'stats';

export interface Filters {
  search: string;
  type: OpportunityType | 'All';
  status: OpportunityStatus | 'All';
  source: string;
  tag: string;
  sortKey: SortKey;
  sortDir: SortDir;
  dueWithin: number;
}

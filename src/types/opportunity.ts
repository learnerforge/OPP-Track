export interface Opportunity {
  id: string;
  title: string;
  type: OpportunityType;
  source: string;
  link: string;
  deadline: string;
  eligibility: string;
  tags: string[];
  status: OpportunityStatus;
  notes: string;
  date_added: string;
  location?: string;
  prize_pool?: string;
  participants?: string;
  organizer?: string;
  duration?: string;
  quality_score?: number;
}

export type OpportunityType = 'Hackathon' | 'Internship' | 'Certification' | 'Competition';

export type OpportunityStatus =
  | 'Not Started'
  | 'Applied'
  | 'In Progress'
  | 'Rejected'
  | 'Completed';

export type UrgencyTier = 'critical' | 'warning' | 'safe' | 'expired';

export type SortKey = 'deadline' | 'date_added' | 'title';

export type SortDir = 'asc' | 'desc';

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

export type ViewMode = 'dashboard' | 'weekly-review' | 'stats';

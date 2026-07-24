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
}

export type OpportunityType = 'Hackathon' | 'Internship' | 'Certification';

export type OpportunityStatus =
  | 'Not Started'
  | 'Applied'
  | 'In Progress'
  | 'Rejected'
  | 'Completed';

export type UrgencyTier = 'critical' | 'warning' | 'safe' | 'expired';

export interface Filters {
  search: string;
  type: OpportunityType | 'All';
  status: OpportunityStatus | 'All';
  source: string;
  tag: string;
}

export type ViewMode = 'dashboard' | 'weekly-review' | 'stats';

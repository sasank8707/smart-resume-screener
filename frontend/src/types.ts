export interface ExperienceEntry {
  organization: string | null;
  role: string | null;
  duration: string | null;
  start_date?: string | null;
  end_date?: string | null;
  responsibilities: string[];
  technologies: string[];
}

export interface EducationEntry {
  institution: string | null;
  degree: string | null;
  field: string | null;
  start_year: number | null;
  end_year: number | null;
}

export interface Candidate {
  id: number;
  candidate_name: string | null;
  email: string | null;
  phone: string | null;
  skills: string[];
  experience: ExperienceEntry[];
  education: EducationEntry[];
  resume_filename: string;
  file_type: "pdf" | "txt";
  parse_provider: string;
  summary: string | null;
  certifications: string[];
  created_at: string;
  updated_at: string;
}

export interface CandidateDetail extends Candidate {
  raw_text: string;
  parsed_data: { summary?: string | null; certifications?: string[] };
}

export interface UploadError {
  filename: string;
  error: string;
}

export interface UploadResponse {
  uploaded: Candidate[];
  errors: UploadError[];
}

export interface JobRequirements {
  required_skills: string[];
  preferred_skills: string[];
  experience_expectations: string | null;
  education_expectations: string[];
  responsibilities: string[];
}

export interface JobDescription {
  id: number;
  title: string;
  description_text?: string;
  requirements: JobRequirements;
  created_at: string;
  updated_at: string;
}

export interface ScreeningResult {
  id: number;
  match_score: number;
  shortlisted: boolean;
  explanation: string;
  strengths: string[];
  missing_skills: string[];
  experience_alignment: string;
  education_alignment: string;
  recommendation: "strong_yes" | "yes" | "maybe" | "no";
  confidence: "low" | "medium" | "high" | null;
  shortlist_threshold: number;
  llm_provider: string;
  llm_model: string | null;
  created_at: string;
  job_description_id: number;
  candidate_id: number;
  candidate_name: string | null;
  candidate_email: string | null;
  candidate_skills: string[];
  candidate_experience: ExperienceEntry[];
  candidate_education: EducationEntry[];
  rank: number | null;
}

export interface ScreeningRunResponse {
  job: JobDescription;
  threshold: number;
  provider_used: string;
  results: ScreeningResult[];
}

export interface RecentActivityItem {
  id: number;
  candidate_id: number;
  candidate_name: string | null;
  job_title: string;
  match_score: number;
  shortlisted: boolean;
  screened_at: string;
}

export interface DashboardStats {
  total_resumes: number;
  candidates_screened: number;
  average_match_score: number;
  shortlisted_count: number;
  total_jobs: number;
  recent_activity: RecentActivityItem[];
}

export interface HealthInfo {
  status: string;
  database: string;
  llm_provider: string;
}

export interface ApiErrorShape {
  message: string;
  status?: number;
  details?: { field: string; issue: string }[];
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

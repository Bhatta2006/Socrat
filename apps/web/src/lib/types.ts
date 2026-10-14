export type Language = 'python' | 'cpp' | 'java';
export type Band = 'not_started' | 'needs_practice' | 'developing' | 'likely_known' | 'strong';
export type Pace = 'support' | 'steady' | 'fast';

export interface Enrollment {
  id: string;
  course: string;
  language: Language;
  status: 'placement' | 'active';
  minutes_per_day: number;
  weekdays: number[];
  goal: Record<string, string | number>;
  level: string;
}

export interface Profile {
  id: string;
  display_name: string | null;
  birth_year: number | null;
  timezone: string | null;
  csrf_token: string;
  onboarded: boolean;
  enrollment: Enrollment | null;
}

export interface Features {
  dev_login: boolean;
  oidc_login: boolean;
  ai_provider: 'anthropic' | 'openai' | 'offline';
  code_execution: boolean;
  execution_backend: string;
  demo_mode: boolean;
}

export interface Course {
  id: string;
  title: string;
  tagline: string;
  description: string;
  languages: Language[];
  levels: { id: string; label: string; description: string }[];
  modules: { id: string; title: string; summary: string; concepts: number }[];
  concept_count: number;
  problem_count: number;
}

export interface PlacementQuestion {
  done: boolean;
  asked: number;
  max_questions?: number;
  question?: {
    id: string;
    topic: string;
    prompt: string;
    kind: string;
    code: string | null;
    options: string[];
  };
}

export interface PlacementSummary {
  asked: number;
  correct: number;
  known_concepts: string[];
  starting_concept: string | null;
}

export type ActivityKind = 'lesson' | 'quiz' | 'problem' | 'checkpoint' | 'review' | 'remedial';

export interface Activity {
  id: string;
  kind: ActivityKind;
  concept: string;
  title: string;
  minutes?: number;
  reason?: string;
  status?: 'done' | 'pending';
}

export interface Revision {
  pace: Pace;
  reasons: string[];
  projected_finish: string;
  remaining_minutes: number;
  at: number;
}

export interface Streak {
  current: number;
  longest: number;
  studied_today: boolean;
  /** Streak freezes banked by meeting a full week's goal; each covers one missed day. */
  freezes: number;
  /** Recent days a freeze covered (ISO dates). */
  frozen: string[];
  week_minutes: number;
  week_goal: number;
}

export interface ProgressNumbers {
  total: number;
  finished: number;
  percent: number;
}

export interface Today {
  greeting: string;
  course: { id: string; title: string };
  language: Language;
  date: string;
  study_day: boolean;
  streak: Streak;
  days_away: number;
  minutes: { done: number; goal: number };
  done: Activity[];
  next: Activity | null;
  queue: Activity[];
  pace: Pace;
  pace_reason: string;
  latest_update: Revision | null;
  reviews_due: number;
  progress: ProgressNumbers;
  projected_finish: string;
}

export interface RoadmapItem {
  lesson_done: boolean;
  quiz_done: boolean;
  review_due: boolean;
  roadmap_resources: { title: string; url: string; source: string; language: string | null }[];
  concept: string;
  title: string;
  module: string;
  status: 'mastered' | 'assumed' | 'practiced' | 'in_progress' | 'upcoming' | 'locked';
  locked_by?: string;
  mastery: number;
  confidence: number;
  minutes: number;
}

export interface PlanView {
  pace: Pace;
  pace_reason: string;
  projected_finish: string;
  remaining_minutes: number;
  target_date: string | null;
  on_track: boolean | null;
  current_concept: string | null;
  modules: {
    id: string;
    title: string;
    summary: string;
    course: string;
    bridge: boolean;
    concepts: RoadmapItem[];
    locked_by: LockInfo | null;
  }[];
  days: { date: string; items: Activity[]; minutes: number }[];
  reasons: string[];
  revisions: Revision[];
  progress: ProgressNumbers;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  goal: number;
  value: number;
  earned: boolean;
  earned_at: number | null;
}

export interface ProgressView {
  modules: {
    id: string;
    title: string;
    concepts: {
      id: string;
      title: string;
      band: Band;
      mastery: number;
      confidence: number;
      evidence: number;
      next_review: number | null;
    }[];
  }[];
  progress: ProgressNumbers;
  streak: Streak;
  achievements: Achievement[];
  heatmap: { day: string; minutes: number; activities: number }[];
  week: { minutes: number; goal: number };
  solves: { independent_solves: number; assisted_solves: number };
  total_minutes: number;
  revisions: Revision[];
  recent: { concept: string; kind: string; score: number; assisted: boolean; at: number }[];
  pace: Pace;
  projected_finish: string;
}

export interface Resource {
  title: string;
  url: string;
  kind: 'article' | 'video' | 'docs' | 'course' | 'book' | 'interactive' | 'visualizer';
  source: string;
  minutes: number;
  level: 'intro' | 'core' | 'deep';
  languages: Language[];
  /** Among the few picked for this learner right now. */
  picked?: boolean;
  opened?: boolean;
  helpful?: boolean | null;
}

export type Platform = 'Socrat' | 'LeetCode' | 'CSES' | 'Codeforces';
export type PracticeStatus = 'todo' | 'attempted' | 'solved';

export interface ExternalProblem {
  id: string;
  title: string;
  /** Opened on click only; never rendered as text. Socrat problems use an in-app path. */
  url: string;
  platform: Platform | string;
  difficulty: 'easy' | 'medium' | 'hard';
  rating?: number | null;
  concepts: string[];
  companies: number;
  striver: boolean;
}

export interface LibraryProblem extends ExternalProblem {
  status: PracticeStatus | null;
  bookmarked: boolean;
  concept: { id: string; title: string; band: Band } | null;
}

export interface Level {
  rating: number;
  name: string;
  next_name: string | null;
  next_rating: number | null;
  progress: number;
}

export interface RecommendedProblem extends ExternalProblem {
  kind: 'review' | 'practice' | 'current' | 'stretch' | 'start' | 'upsolve';
  reason: string;
  concept: { id: string; title: string; band: Band };
  status: PracticeStatus | null;
}

export interface CodeforcesAccount {
  handle: string;
  rating: number | null;
  max_rating: number | null;
  rank: string;
  solved: number;
  attempted: number;
  weak_tags: string[];
  synced_at: number | null;
  sync_error: string;
}

export interface Recommendations {
  level: Level;
  problems: RecommendedProblem[];
  topics: { id: string; title: string; summary: string; reason: string; kind: string; band: Band; minutes: number }[];
  solved_external: number;
  codeforces: CodeforcesAccount | null;
}

export interface CompanyProblem extends ExternalProblem {
  frequency: number;
  window: 'thirty-days' | 'three-months' | 'six-months' | 'more-than-six-months' | 'all';
  concept: { id: string; title: string; band: Band } | null;
}

export interface ConceptView {
  exercises: { number: number; title: string; url: string; language: string; guidance: string }[];
  id: string;
  course: string;
  title: string;
  summary: string;
  module: string;
  lesson: string;
  key_points: string[];
  pitfalls: string[];
  resources: Resource[];
  practice_links: { title: string; url: string; platform: string; difficulty: 'easy' | 'medium' | 'hard' }[];
  more_practice: LibraryProblem[];
  implementations: { title: string; url: string }[];
  handbook: { chapter: string; title: string; page: number; url: string; source: string }[];
  problems: { id: string; title: string; difficulty: string; solved: boolean }[];
  prerequisites: { id: string; title: string; band: Band }[];
  band: Band;
  lesson_done: boolean;
  quiz_done: boolean;
  locked: LockInfo | null;
  language: Language;
}

export interface QuizQuestion {
  id: string;
  concept: string;
  concept_title: string;
  kind: string;
  prompt: string;
  code: string | null;
  options: string[];
  difficulty: number;
  answered: boolean;
  choice: number | null;
  correct?: boolean;
  answer?: number;
  explanation?: string;
}

export interface QuizSession {
  id: string;
  activity_id: string;
  questions: QuizQuestion[];
  completed: boolean;
  score: number | null;
  feedback: 'immediate' | 'at_end';
  gate?: Gate;
}

/** A checkpoint that unlocks the next module: an adaptive staircase graded at the end. */
export interface Gate {
  max_items: number;
  max_strikes: number;
  strikes: number;
  levels: number[];
  level: number;
  hard_level: number;
  hard_needed: number;
  hard_correct: number;
  pass_score: number;
  score: number | null;
  passed: boolean | null;
  retry_at: number | null;
  attempts: number;
  module: string;
  unlocks: string | null;
}

export interface LockInfo {
  gate: string;
  module: string;
}

export interface Case {
  status: string;
  wall_ms: number;
  public: boolean;
  input: string | null;
  expected: string | null;
  stdout: string | null;
  stderr: string | null;
}

export interface Submission {
  id: string;
  problem_id: string;
  language: Language;
  mode: 'run' | 'submit';
  status: 'queued' | 'running' | 'done' | string;
  verdict: string;
  passed: number;
  total: number;
  cases: Case[];
  assistance: number;
  created_at: number;
  finished_at: number | null;
}

export interface ProblemView {
  id: string;
  locked: LockInfo | null;
  title: string;
  difficulty: string;
  concept: { id: string; title: string };
  statement: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  examples: { input: string; output: string; explanation?: string }[];
  language: Language;
  starter: string;
  draft: string | null;
  solved: boolean;
  history: {
    id: string;
    mode: string;
    verdict: string;
    status: string;
    passed: number;
    total: number;
    at: number;
  }[];
  hint_count: number;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  level?: number | null;
  rating?: number | null;
}

export interface AssessmentStatus {
  state: 'locked' | 'available' | 'in_progress' | 'done';
  week: string;
  id: string | null;
  topics: string[];
  questions?: number;
  time_limit_minutes?: number;
  needed: number;
}

export interface AssessmentReport {
  correct: number;
  questions: number;
  coding_solved: number;
  coding_total: number;
  minutes: number;
  previous_score: number | null;
  topics: { id: string; title: string; correct: number; total: number; before: number; after: number; band: Band }[];
  strengths: string[];
  focus: { id: string; title: string }[];
}

export interface AssessmentView {
  id: string;
  week: string;
  timed: boolean;
  started_at: number;
  deadline: number | null;
  seconds_left: number | null;
  finished: boolean;
  score: number | null;
  topics: { id: string; title: string; reason: 'studied' | 'review' }[];
  questions: QuizQuestion[];
  coding: { id: string; title: string; difficulty: string; concept: string; solved: boolean }[];
  report: AssessmentReport | null;
}

export interface SprintView {
  id: string;
  started_at: number;
  deadline: number;
  seconds_left: number | null;
  finished: boolean;
  solved: number;
  problems: { id: string; title: string; difficulty: string; concept: string; solved_after: number | null }[];
}

export interface Contest {
  id: number;
  name: string;
  start: number;
  duration_minutes: number;
  url: string;
}

export type AssessmentType = "Rx Check" | "Dispensing" | "Med Recon" | "MiniCeX";
export type AllocationStatus =
  | "Allocated"
  | "Unallocated"
  | "Skipped - Already Passed"
  | "Skipped - Already Allocated"
  | "Skipped - Not Applicable"
  | "Skipped - Unsupported Cell State";

export interface AllocationRecord {
  date: string;
  assesseeName: string;
  glfSectionHeader: string;
  assessmentType: AssessmentType;
  assesseeLocation: string;
  assignedAssessor: string;
  assessorGlfAvailabilityDate: string;
  assessorGlfAvailabilityType: string;
  status: AllocationStatus;
  reason: string;
  originalGlfCellReference: string;
  existingAllocationHistory: string;
}

export interface AllocationSummary {
  allocated: number;
  unallocated: number;
  skipped: number;
}

export interface RosterSummary {
  allAssessors: string[];
  availableAssessorsByDate: Record<string, string[]>;
}

export interface GenerateAllocationResponse {
  success: boolean;
  summary: AllocationSummary;
  records: AllocationRecord[];
  roster: RosterSummary;
  download_id: string;
  preview_download_id: string;
}

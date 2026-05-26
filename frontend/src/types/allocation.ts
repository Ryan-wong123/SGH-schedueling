export type AssessmentType = "Rx Check" | "Dispensing" | "Med Recon" | "MiniCeX";
export type LocationType = "Ward" | "OPS" | "Unknown" | "";
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
  assesseeLocation: LocationType;
  assignedAssessor: string;
  assessorGlfAvailabilityDate: string;
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

export interface GenerateAllocationResponse {
  success: boolean;
  summary: AllocationSummary;
  records: AllocationRecord[];
  download_id: string;
}

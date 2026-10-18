import type { AllocationRecord } from "../types/allocation";

interface Props {
  records: AllocationRecord[];
}

export function ResultsTable({ records }: Props) {
  return (
    <div className="table-wrap">
      {records.length === 0 ? <div className="empty-state">No records match this filter.</div> : null}
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Assessee</th>
            <th>Header</th>
            <th>Assessment</th>
            <th>Location</th>
            <th>Assessor</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Cell</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={`${record.originalGlfCellReference}-${index}`} className={record.status === "Unallocated" ? "warn" : ""}>
              <td>{record.date}</td>
              <td>{record.assesseeName}</td>
              <td>{record.glfSectionHeader}</td>
              <td>{record.assessmentType}</td>
              <td>{record.assesseeLocation}</td>
              <td>{record.assignedAssessor}</td>
              <td>{record.status}</td>
              <td>{record.reason || record.existingAllocationHistory}</td>
              <td>{record.originalGlfCellReference}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

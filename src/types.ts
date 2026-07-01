export interface LabTest {
  test_name: string;
  value: number;
  unit: string;
  ref_low: number;
  ref_high: number;
  category: string;
}

export interface ReportData {
  patient_name: string;
  report_date: string;
  tests: LabTest[];
}

export type Procedure = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  legal_basis: string[] | null;
  processing_time_days: number | null;
  fee_vnd: number | null;
  competent_authority: string | null;
  is_online: boolean;
  category_id: string | null;
  created_at: string;
};

export type ProcedureDependency = {
  procedure_id: string;
  depends_on_procedure_id: string;
  is_mandatory: boolean;
  condition_description: string | null;
};

export type ProcedureStep = {
  procedure_id: string;
  procedure_name: string;
  status: "completed" | "pending" | "blocked";
  order: number;
};

export type ProcedureExecutionPlan = {
  target_procedure_id: string;
  steps: ProcedureStep[];
  missing_documents: string[];
};

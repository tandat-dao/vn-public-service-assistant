import type { Procedure, ProcedureExecutionPlan } from "../types/procedure";
import { apiClient } from "./client";

export async function listProcedures(): Promise<Procedure[]> {
  const { data } = await apiClient.get<Procedure[]>("/procedures");
  return data;
}

export async function getProcedure(id: string): Promise<Procedure> {
  const { data } = await apiClient.get<Procedure>(`/procedures/${id}`);
  return data;
}

export async function getProcedurePlan(id: string): Promise<ProcedureExecutionPlan> {
  const { data } = await apiClient.get<ProcedureExecutionPlan>(`/procedures/${id}/plan`);
  return data;
}

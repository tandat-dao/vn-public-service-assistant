import type { ProcedureExecutionPlan } from "./procedure";

export type ChatRequest = {
  message: string;
  session_id: string;
  image_path: string | null;
};

export type Citation = {
  doc_id: string;
  document_number: string;
  article: string;
  excerpt: string;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  execution_plan: ProcedureExecutionPlan | null;
  confidence: "high" | "medium" | "low";
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  execution_plan?: ProcedureExecutionPlan | null;
};
